import os
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from dotenv import load_dotenv

load_dotenv()

# Получаем переменные окружения
BOT_TOKEN = "7719717032:AAG4GwZp_2CRecHJ4mrsKKSIntgUsgqggEk"
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://tap-wars.onrender.com")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не установлен!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== КЛАВИАТУРЫ ==========

def get_main_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎮 Играть"), KeyboardButton(text="🏆 Топ игроков")],
            [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="❓ Помощь")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_inline_menu() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎮 Запустить игру", web_app=WebAppInfo(url=WEBAPP_URL))],
            [InlineKeyboardButton(text="❓ Помощь", callback_data="help")]
        ]
    )
    return keyboard

# ========== ОБРАБОТЧИКИ ==========

@dp.message(Command("start"))
async def start(message: types.Message):
    user_name = message.from_user.first_name
    welcome_text = (
        f"⚡ Добро пожаловать в Tap Wars, {user_name}!\n\n"
        f"🎮 **Tap Wars** — игра, где нужно быстро тапать!\n\n"
        f"**📊 Режимы:**\n"
        f"🟢 Мини — 10⭐, 10 игроков, приз 60⭐\n"
        f"🔵 Стандарт — 50⭐, 20 игроков, приз 750⭐\n"
        f"🟣 VIP — 100⭐, 10 игроков, приз 750⭐\n"
        f"⚔️ Дуэль — 10⭐, 2 игрока, победитель забирает 15⭐\n\n"
        f"👇 Нажми на кнопку ниже!"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@dp.message(lambda message: message.text == "🎮 Играть")
async def play_button(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎮 Запустить Tap Wars", web_app=WebAppInfo(url=WEBAPP_URL))]
        ]
    )
    await message.answer("🎮 Нажми на кнопку ниже, чтобы запустить игру!", reply_markup=keyboard)

@dp.message(lambda message: message.text == "🏆 Топ игроков")
async def leaderboard_button(message: types.Message):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{WEBAPP_URL}/api/leaderboard", timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("leaders") and len(data["leaders"]) > 0:
                        text = "🏆 **Топ игроков Tap Wars** 🏆\n\n"
                        for i, player in enumerate(data["leaders"][:10]):
                            medal = "🥇 " if i == 0 else "🥈 " if i == 1 else "🥉 " if i == 2 else ""
                            name = player.get("full_name") or player.get("username") or f"Player {player.get('user_id')}"
                            text += f"{medal}{i+1}. {name} — {player.get('score', 0)} 👆\n"
                        await message.answer(text, parse_mode="Markdown")
                    else:
                        await message.answer("🏆 Пока нет игроков в топе! Будь первым!")
                else:
                    await message.answer("❌ Сервер временно недоступен. Попробуй позже.")
    except Exception as e:
        print(f"Error: {e}")
        await message.answer("❌ Не удалось загрузить топ игроков.")

@dp.message(lambda message: message.text == "💰 Баланс")
async def balance_button(message: types.Message):
    user_id = message.from_user.id
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{WEBAPP_URL}/api/balance/{user_id}", timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("success"):
                        balance = data.get("balance", 0)
                        await message.answer(
                            f"💰 **Твой баланс:** {balance} ⭐\n\n"
                            f"💡 **Как заработать?**\n"
                            f"• Побеждай в играх\n"
                            f"• Забирай призовой фонд\n\n"
                            f"🎮 Нажми 'Играть', чтобы начать!",
                            parse_mode="Markdown",
                            reply_markup=get_inline_menu()
                        )
                    else:
                        await message.answer("❌ Пользователь не найден. Начни игру!")
                else:
                    await message.answer("❌ Сервер недоступен.")
    except Exception as e:
        print(f"Error: {e}")
        await message.answer("❌ Не удалось загрузить баланс.")

@dp.message(lambda message: message.text == "❓ Помощь")
async def help_button(message: types.Message):
    help_text = (
        "❓ **Помощь по игре Tap Wars**\n\n"
        "**🎮 Как играть?**\n"
        "1. Нажми 'Играть'\n"
        "2. Купи билет за Stars или TON\n"
        "3. Жди набора игроков\n"
        "4. Тапай 30-60 секунд\n"
        "5. Попади в топ и получи приз!\n\n"
        "**💎 Способы оплаты:**\n"
        "• ⭐ **Telegram Stars** — покупка через App Store/Google Play\n"
        "• 💎 **TON** — криптовалюта, комиссия 0%, нужен TON кошелёк\n\n"
        "**⚔️ Режимы игры:**\n"
        "• 🟢 Мини — 10⭐, топ-3 получают 35/15/10⭐\n"
        "• 🔵 Стандарт — 50⭐, топ-5 получают 300/200/120/80/50⭐\n"
        "• 🟣 VIP — 100⭐, топ-5 получают 400/250/100⭐\n"
        "• ⚔️ Дуэль — 10⭐, победитель забирает 15⭐\n\n"
        "**💰 Вывод средств:**\n"
        "• Минимальная сумма: 100⭐\n"
        "• Запрос обрабатывается до 24 часов\n\n"
        "**📞 Поддержка:**\n"
        "• По вопросам пишите в чат бота"
    )
    await message.answer(help_text, parse_mode="Markdown")

@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    if callback.data == "help":
        await help_button(callback.message)
        await callback.answer()
    else:
        await callback.answer()

# ========== ЗАПУСК ==========

async def main():
    print("🤖 Бот Tap Wars запущен!")
    print(f"📱 WebApp URL: {WEBAPP_URL}")
    
    # Удаляем вебхук при запуске
    await bot.delete_webhook()
    print("✅ Webhook удалён")
    
    print("✅ Бот готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
