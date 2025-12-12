import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_IDS
import database as db

bot = Bot(token=8515977024:AAEmdj66SSD9NuM27bRcWkrHDSJfhOygftU)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# States
class Registration(StatesGroup):
    username = State()
    password = State()

class ActivateKey(StatesGroup):
    waiting_key = State()

class AdminCreateKey(StatesGroup):
    key = State()
    key_type = State()
    days = State()

# Keyboards
def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Купить подписку", callback_data="buy")],
        [InlineKeyboardButton(text="🔑 Активировать ключ", callback_data="activate_key")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="📥 Скачать чит", callback_data="download")]
    ])

def get_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Все пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="🔑 Создать ключ", callback_data="admin_create_key")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
    ])

def get_buy_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Basic - 199₽/мес", callback_data="buy_basic")],
        [InlineKeyboardButton(text="💎 Premium - 399₽/мес", callback_data="buy_premium")],
        [InlineKeyboardButton(text="👑 Lifetime - 999₽", callback_data="buy_lifetime")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
    ])

def get_back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
    ])

# Start command
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    
    if await db.is_registered(message.from_user.id):
        await message.answer(
            "👋 С возвращением в **Dick Client**!\n\n"
            "Выберите действие:",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    else:
        await message.answer(
            "👋 Добро пожаловать в **Dick Client**!\n\n"
            "Для начала работы необходимо зарегистрироваться.\n\n"
            "📝 Введите ваш **никнейм**:",
            parse_mode="Markdown"
        )
        await state.set_state(Registration.username)

# Registration
@dp.message(Registration.username)
async def process_username(message: Message, state: FSMContext):
    username = message.text.strip()
    
    if len(username) < 3 or len(username) > 16:
        await message.answer("❌ Никнейм должен быть от 3 до 16 символов. Попробуйте снова:")
        return
    
    await state.update_data(username=username)
    await message.answer(
        f"✅ Никнейм: **{username}**\n\n"
        "🔐 Теперь введите **пароль** (минимум 6 символов):",
        parse_mode="Markdown"
    )
    await state.set_state(Registration.password)

@dp.message(Registration.password)
async def process_password(message: Message, state: FSMContext):
    password = message.text.strip()
    
    if len(password) < 6:
        await message.answer("❌ Пароль должен быть минимум 6 символов. Попробуйте снова:")
        return
    
    data = await state.get_data()
    username = data["username"]
    
    success = await db.register_user(message.from_user.id, username, password)
    
    if success:
        await message.delete()  # Удаляем сообщение с паролем
        await message.answer(
            "✅ **Регистрация успешна!**\n\n"
            f"👤 Никнейм: {username}\n"
            "🔐 Пароль сохранён\n\n"
            "Выберите действие:",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard()
        )
    else:
        await message.answer("❌ Ошибка регистрации. Вы уже зарегистрированы!")
    
    await state.clear()

# Main menu callback
@dp.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🎮 **Dick Client** - Главное меню\n\n"
        "Выберите действие:",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

# Profile
@dp.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    
    if not user:
        await callback.answer("❌ Вы не зарегистрированы!")
        return
    
    sub_status = "❌ Нет подписки"
    if user["subscription_type"] != "none" and user["subscription_until"]:
        from datetime import datetime
        until = datetime.fromisoformat(user["subscription_until"])
        if until > datetime.now():
            sub_status = f"✅ {user['subscription_type'].upper()} до {until.strftime('%d.%m.%Y')}"
        else:
            sub_status = "⏰ Подписка истекла"
    
    await callback.message.edit_text(
        f"👤 **Ваш профиль**\n\n"
        f"📛 Никнейм: `{user['username']}`\n"
        f"🆔 ID: `{user['user_id']}`\n"
        f"📅 Регистрация: {user['registered_at'][:10]}\n"
        f"💎 Подписка: {sub_status}\n",
        parse_mode="Markdown",
        reply_markup=get_back_keyboard()
    )

# Buy subscription
@dp.callback_query(F.data == "buy")
async def show_buy_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🛒 **Выберите подписку:**\n\n"
        "⭐ **Basic** - 199₽/мес\n"
        "   • KillAura, ESP, Fly\n\n"
        "💎 **Premium** - 399₽/мес\n"
        "   • Все функции Basic\n"
        "   • ElytraFly, AntiCheat Bypass\n\n"
        "👑 **Lifetime** - 999₽ навсегда\n"
        "   • Все функции Premium\n"
        "   • Приоритетная поддержка\n",
        parse_mode="Markdown",
        reply_markup=get_buy_keyboard()
    )

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: CallbackQuery):
    plan = callback.data.replace("buy_", "")
    
    prices = {"basic": 199, "premium": 399, "lifetime": 999}
    
    await callback.message.edit_text(
        f"💳 **Оплата подписки {plan.upper()}**\n\n"
        f"💰 Сумма: {prices[plan]}₽\n\n"
        "📱 Для оплаты свяжитесь с администратором:\n"
        "@admin_username\n\n"
        "Или оплатите по реквизитам:\n"
        "`4276 XXXX XXXX XXXX`\n\n"
        "После оплаты отправьте скриншот администратору.",
        parse_mode="Markdown",
        reply_markup=get_back_keyboard()
    )

# Activate key
@dp.callback_query(F.data == "activate_key")
async def activate_key_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🔑 **Активация ключа**\n\n"
        "Введите ваш ключ активации:",
        parse_mode="Markdown"
    )
    await state.set_state(ActivateKey.waiting_key)

@dp.message(ActivateKey.waiting_key)
async def process_key(message: Message, state: FSMContext):
    key = message.text.strip()
    
    success, result_message = await db.activate_key(message.from_user.id, key)
    
    if success:
        await message.answer(
            f"✅ {result_message}",
            reply_markup=get_back_keyboard()
        )
    else:
        await message.answer(
            f"❌ {result_message}",
            reply_markup=get_back_keyboard()
        )
    
    await state.clear()

# Download
@dp.callback_query(F.data == "download")
async def download_client(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    
    has_subscription = False
    if user and user["subscription_type"] != "none" and user["subscription_until"]:
        from datetime import datetime
        until = datetime.fromisoformat(user["subscription_until"])
        if until > datetime.now():
            has_subscription = True
    
    if has_subscription:
        await callback.message.edit_text(
            "📥 **Скачать Dick Client**\n\n"
            "🔗 Ссылка для скачивания:\n"
            "[Скачать с Google Drive](https://drive.google.com/your-link)\n\n"
            "📋 Инструкция:\n"
            "1. Скачайте архив\n"
            "2. Распакуйте в папку mods\n"
            "3. Запустите Minecraft 1.16.5\n"
            "4. Откройте чит клавишей `RSHIFT`\n\n"
            "❓ Проблемы? Пишите @admin_username",
            parse_mode="Markdown",
            reply_markup=get_back_keyboard()
        )
    else:
        await callback.message.edit_text(
            "❌ **Доступ запрещён**\n\n"
            "Для скачивания чита необходима активная подписка.\n\n"
            "Купите подписку или активируйте ключ.",
            parse_mode="Markdown",
            reply_markup=get_back_keyboard()
        )

# Admin commands
@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет доступа к админ-панели!")
        return
    
    await message.answer(
        "🔧 **Админ-панель Dick Client**\n\n"
        "Выберите действие:",
        parse_mode="Markdown",
        reply_markup=get_admin_keyboard()
    )

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа!")
        return
    
    stats = await db.get_stats()
    
    await callback.message.edit_text(
        "📊 **Статистика Dick Client**\n\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"💎 С подпиской: {stats['subscribers']}\n"
        f"🔑 Использовано ключей: {stats['used_keys']}\n"
        f"🔓 Доступных ключей: {stats['available_keys']}\n"
        f"💰 Всего покупок: {stats['total_purchases']}\n",
        parse_mode="Markdown",
        reply_markup=get_admin_keyboard()
    )

@dp.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа!")
        return
    
    users = await db.get_all_users()
    
    if not users:
        text = "👥 **Пользователи**\n\nПока нет зарегистрированных пользователей."
    else:
        text = "👥 **Пользователи** (последние 10):\n\n"
        for user in users[:10]:
            sub = "✅" if user["subscription_type"] != "none" else "❌"
            text += f"{sub} `{user['username']}` (ID: {user['user_id']})\n"
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=get_admin_keyboard()
    )

@dp.callback_query(F.data == "admin_create_key")
async def admin_create_key(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ Нет доступа!")
        return
    
    await callback.message.edit_text(
        "🔑 **Создание ключа**\n\n"
        "Введите ключ (или отправьте `random` для случайного):",
        parse_mode="Markdown"
    )
    await state.set_state(AdminCreateKey.key)

@dp.message(AdminCreateKey.key)
async def process_admin_key(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    key = message.text.strip()
    if key.lower() == "random":
        import secrets
        key = f"DICK-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"
    
    await state.update_data(key=key)
    await message.answer(
        f"🔑 Ключ: `{key}`\n\n"
        "Выберите тип подписки:\n"
        "Отправьте: `basic`, `premium` или `lifetime`",
        parse_mode="Markdown"
    )
    await state.set_state(AdminCreateKey.key_type)

@dp.message(AdminCreateKey.key_type)
async def process_admin_key_type(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    key_type = message.text.strip().lower()
    if key_type not in ["basic", "premium", "lifetime"]:
        await message.answer("❌ Неверный тип! Введите: basic, premium или lifetime")
        return
    
    await state.update_data(key_type=key_type)
    await message.answer(
        "📅 Введите количество дней подписки (число):\n"
        "(Для lifetime введите 9999)"
    )
    await state.set_state(AdminCreateKey.days)

@dp.message(AdminCreateKey.days)
async def process_admin_days(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    try:
        days = int(message.text.strip())
    except:
        await message.answer("❌ Введите число!")
        return
    
    data = await state.get_data()
    key = data["key"]
    key_type = data["key_type"]
    
    success = await db.create_key(key, key_type, days)
    
    if success:
        await message.answer(
            f"✅ **Ключ создан!**\n\n"
            f"🔑 Ключ: `{key}`\n"
            f"💎 Тип: {key_type.upper()}\n"
            f"📅 Дней: {days}",
            parse_mode="Markdown",
            reply_markup=get_admin_keyboard()
        )
    else:
        await message.answer(
            "❌ Ошибка создания ключа (возможно, ключ уже существует)",
            reply_markup=get_admin_keyboard()
        )
    
    await state.clear()

# Run bot
async def main():
    await db.init_db()
    print("🤖 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":

    asyncio.run(main())
