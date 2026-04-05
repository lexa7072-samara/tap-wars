import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.enums import ContentType

# Получаем переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://tap-wars.onrender.com")

# Проверка токена
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен в переменных окружения!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== КЛАВИАТУРЫ ==========

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура с кнопками"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🎮 Играть"),
                KeyboardButton(text="🏆 Топ игроков")
            ],
            [
                KeyboardButton(text="💰 Баланс"),
                KeyboardButton(text="❓ Помощь")
            ]
        ],
        resize_keyboard=True  # Автоматически подгонять размер
    )
    return keyboard

def get_game_selector_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора типа игры"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🟢 Мини (10⭐)",
                    web_app=WebAppInfo(url=f"{WEBAPP_URL}?game=mini")
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔵 Стандарт (50⭐)",
                    web_app=WebAppInfo(url=f"{WEBAPP_URL}?game=standard")
                )
            ],
            [
                InlineKeyboardButton(
                    text="🟣 VIP (100⭐)",
                    web_app=WebAppInfo(url=f"{WEBAPP_URL}?game=vip")
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚔️ Дуэль (10⭐)",
                    web_app=WebAppInfo(url=f"{WEBAPP_URL}?game=duel")
                )
            ]
        ]
    )
    return keyboard

def get_inline_menu() -> InlineKeyboardMarkup:
    """Инлайн клавиатура для сообщений"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🎮 Открыть игру",
                    web_app=WebAppInfo(url=WEBAPP_URL)
                )
            ],
            [
                InlineKeyboardButton(
                    text="📢 Наш канал",
                    url="https://t.me/your_channel"  # Замените на ваш канал
                ),
                InlineKeyboardButton(
                    text="💬 Чат",
                    url="https://t.me/your_chat"  # Замените на ваш чат
                )
            ],
            [
                InlineKeyboardButton(
                    text="❓ Помощь",
                    callback_data="help"
                )
            ]
        ]
    )
    return keyboard

# ========== ОБРАБОТЧИКИ КОМАНД ==========

@dp.message(Command("start"))
async def start(message: types.Message):
    """Обработчик команды /start"""
    user_name = message.from_user.first_name
    
    # Приветственное сообщение
    welcome_text = (
        f"⚡ Добро пожаловать в Tap Wars, {user_name}!\n\n"
        f"🎮 **Tap Wars** — это увлекательная игра, где нужно быстро тапать!\n\n"
        f"**📊 Доступные режимы:**\n"
        f"🟢 Мини — 10⭐, 10 игроков, приз 60⭐\n"
        f"🔵 Стандарт — 50⭐, 20 игроков, приз 750⭐\n"
        f"🟣 VIP — 100⭐, 10 игроков, приз 750⭐\n"
        f"⚔️ Дуэль — 10⭐, 2 игрока, победитель забирает 15⭐\n\n"
        f"👇 Нажми на кнопку ниже, чтобы начать!"
    )
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@dp.message(lambda message: message.text == "🎮 Играть")
async def play_button(message: types.Message):
    """Кнопка 'Играть'"""
    await message.answer(
        "🎮 **Выбери режим игры:**\n\n"
        "🟢 **Мини** — 10⭐, 10 игроков, 60⭐ призовой фонд\n"
        "🔵 **Стандарт** — 50⭐, 20 игроков, 750⭐ призовой фонд\n"
        "🟣 **VIP** — 100⭐, 10 игроков, 750⭐ призовой фонд\n"
        "⚔️ **Дуэль** — 10⭐, 2 игрока, победитель забирает 15⭐",
        reply_markup=get_game_selector_keyboard(),
        parse_mode="Markdown"
    )

@dp.message(lambda message: message.text == "🏆 Топ игроков")
async def leaderboard_button(message: types.Message):
    """Кнопка 'Топ игроков'"""
    import aiohttp
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{WEBAPP_URL}/api/leaderboard") as response:
                data = await response.json()
                
                if data.get("leaders") and len(data["leaders"]) > 0:
                    text = "🏆 **Топ игроков Tap Wars** 🏆\n\n"
                    for i, player in enumerate(data["leaders"][:10]):
                        medal = ""
                        if i == 0:
                            medal = "🥇 "
                        elif i == 1:
                            medal = "🥈 "
                        elif i == 2:
                            medal = "🥉 "
                        
                        name = player.get("full_name") or player.get("username") or f"Player {player.get('user_id')}"
                        score = player.get("score", 0)
                        text += f"{medal}{i+1}. {name} — {score} 👆\n"
                    
                    await message.answer(text, parse_mode="Markdown")
                else:
                    await message.answer("🏆 Пока нет игроков в топе! Будь первым!")
    except Exception as e:
        print(f"Error getting leaderboard: {e}")
        await message.answer("❌ Не удалось загрузить топ игроков. Попробуй позже.")

@dp.message(lambda message: message.text == "💰 Баланс")
async def balance_button(message: types.Message):
    """Кнопка 'Баланс'"""
    user_id = message.from_user.id
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{WEBAPP_URL}/api/balance/{user_id}") as response:
                data = await response.json()
                
                if data.get("success"):
                    balance = data.get("balance", 0)
                    await message.answer(
                        f"💰 **Твой баланс:** {balance} ⭐\n\n"
                        f"💡 **Как заработать звезды?**\n"
                        f"• Побеждай в играх и забирай призовой фонд\n"
                        f"• Приглашай друзей (скоро)\n"
                        f"• Выполняй ежедневные задания (скоро)\n\n"
                        f"🎮 Нажми 'Играть', чтобы начать!",
                        parse_mode="Markdown",
                        reply_markup=get_inline_menu()
                    )
                else:
                    await message.answer("❌ Не удалось загрузить баланс. Попробуй позже.")
    except Exception as e:
        print(f"Error getting balance: {e}")
        await message.answer("❌ Не удалось загрузить баланс. Попробуй позже.")

@dp.message(lambda message: message.text == "❓ Помощь")
async def help_button(message: types.Message):
    """Кнопка 'Помощь'"""
    help_text = (
        "❓ **Помощь по игре Tap Wars**\n\n"
        "**🎮 Как играть?**\n"
        "1. Выбери режим игры\n"
        "2. Купи билет за Telegram Stars\n"
        "3. Жди набора игроков\n"
        "4. Тапай как можно быстрее 30-60 секунд\n"
        "5. Попади в топ и получи приз!\n\n"
        "**⚔️ Режимы игры:**\n"
        "• 🟢 Мини — 10⭐, 10 игроков, топ-3 получают призы\n"
        "• 🔵 Стандарт — 50⭐, 20 игроков, топ-5 получают призы\n"
        "• 🟣 VIP — 100⭐, 10 игроков, топ-5 получают призы\n"
        "• ⚔️ Дуэль — 10⭐, 2 игрока, победитель забирает всё\n\n"
        "**💰 Вывод средств:**\n"
        "• Минимальная сумма вывода: 100⭐\n"
        "• Запрос обрабатывается до 24 часов\n"
        "• Вывод происходит в Telegram Stars\n\n"
        "**📞 Контакты:**\n"
        "• По вопросам: @your_support"  # Замените на ваш контакт
    )
    
    await message.answer(help_text, parse_mode="Markdown")

@dp.message(Command("balance"))
async def balance_command(message: types.Message):
    """Команда /balance"""
    await balance_button(message)

@dp.message(Command("top"))
async def top_command(message: types.Message):
    """Команда /top"""
    await leaderboard_button(message)

@dp.message(Command("help"))
async def help_command(message: types.Message):
    """Команда /help"""
    await help_button(message)

@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    """Обработчик инлайн кнопок"""
    if callback.data == "help":
        await help_button(callback.message)
        await callback.answer()
    else:
        await callback.answer()

# ========== ЗАПУСК БОТА ==========

async def main():
    print("🤖 Бот Tap Wars запущен!")
    print(f"📱 WebApp URL: {WEBAPP_URL}")
    print("✅ Бот готов к работе!")
    
    # Запускаем поллинг
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
