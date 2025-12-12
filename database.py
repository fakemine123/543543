import aiosqlite
import hashlib
from datetime import datetime

DATABASE_PATH = "bot_database.db"

async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                registered_at TEXT NOT NULL,
                subscription_type TEXT DEFAULT 'none',
                subscription_until TEXT DEFAULT NULL,
                activated_key TEXT DEFAULT NULL,
                is_banned INTEGER DEFAULT 0
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS keys (
                key TEXT PRIMARY KEY,
                key_type TEXT NOT NULL,
                days INTEGER NOT NULL,
                used_by INTEGER DEFAULT NULL,
                created_at TEXT NOT NULL,
                used_at TEXT DEFAULT NULL
            )
        ''')
        
        await db.execute('''
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                purchase_type TEXT NOT NULL,
                amount REAL NOT NULL,
                purchased_at TEXT NOT NULL
            )
        ''')
        
        await db.commit()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

async def is_registered(user_id: int) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
        )
        return await cursor.fetchone() is not None

async def register_user(user_id: int, username: str, password: str) -> bool:
    if await is_registered(user_id):
        return False
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO users (user_id, username, password_hash, registered_at) VALUES (?, ?, ?, ?)",
            (user_id, username, hash_password(password), datetime.now().isoformat())
        )
        await db.commit()
    return True

async def get_user(user_id: int) -> dict:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
    return None

async def activate_key(user_id: int, key: str) -> tuple:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT * FROM keys WHERE key = ? AND used_by IS NULL", (key,)
        )
        key_data = await cursor.fetchone()
        
        if not key_data:
            return False, "Ключ не найден или уже использован"
        
        key_type = key_data[1]
        days = key_data[2]
        
        from datetime import timedelta
        subscription_until = (datetime.now() + timedelta(days=days)).isoformat()
        
        await db.execute(
            "UPDATE users SET subscription_type = ?, subscription_until = ?, activated_key = ? WHERE user_id = ?",
            (key_type, subscription_until, key, user_id)
        )
        
        await db.execute(
            "UPDATE keys SET used_by = ?, used_at = ? WHERE key = ?",
            (user_id, datetime.now().isoformat(), key)
        )
        
        await db.commit()
        return True, f"Ключ активирован! Подписка: {key_type} на {days} дней"

async def create_key(key: str, key_type: str, days: int) -> bool:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO keys (key, key_type, days, created_at) VALUES (?, ?, ?, ?)",
                (key, key_type, days, datetime.now().isoformat())
            )
            await db.commit()
            return True
        except:
            return False

async def get_stats() -> dict:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor.fetchone())[0]
        
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE subscription_type != 'none'")
        subscribers = (await cursor.fetchone())[0]
        
        cursor = await db.execute("SELECT COUNT(*) FROM keys WHERE used_by IS NOT NULL")
        used_keys = (await cursor.fetchone())[0]
        
        cursor = await db.execute("SELECT COUNT(*) FROM keys WHERE used_by IS NULL")
        available_keys = (await cursor.fetchone())[0]
        
        cursor = await db.execute("SELECT COUNT(*) FROM purchases")
        total_purchases = (await cursor.fetchone())[0]
        
    return {
        "total_users": total_users,
        "subscribers": subscribers,
        "used_keys": used_keys,
        "available_keys": available_keys,
        "total_purchases": total_purchases
    }

async def get_all_users() -> list:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users ORDER BY registered_at DESC")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def add_purchase(user_id: int, purchase_type: str, amount: float):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO purchases (user_id, purchase_type, amount, purchased_at) VALUES (?, ?, ?, ?)",
            (user_id, purchase_type, amount, datetime.now().isoformat())
        )
        await db.commit()