from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import logging

BOT_TOKEN = "7719717032:AAG4GwZp_2CRecHJ4mrsKKSIntgUsgqggEk"
WEB_APP_URL = "https://tap-wars.onrender.com/"  # URL где хостится фронтенд

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🎮 ИГРАТЬ В TAP WARS",
            web_app=WebAppInfo(url=https://tap-wars.onrender.com/)
        )],
        [InlineKeyboardButton(text="ℹ️ О игре", callback_data="about")],
        [InlineKeyboardButton(text="🏆 Топ игроков", callback_data="top")]
    ])
    
    await message.answer(
        "🎮 <b>TAP WARS: Battle Royale</b>\n\n"
        "Соревнуйся с другими игроками в скорости тапа!\n\n"
        "💰 Реальные призы в Stars\n"
        "🏆 60 секунд адреналина\n"
        "👥 50 игроков в раунде\n\n"
        "Нажми кнопку ниже чтобы начать! 🚀",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@dp.callback_query(lambda c: c.data == "about")
async def about_game(callback: types.CallbackQuery):
    await callback.message.answer(
        "📖 <b>Как играть:</b>\n\n"
        "1. Купи билет за 50 ⭐\n"
        "2. Дождись 50 игроков\n"
        "3. Тапай 60 секунд\n"
        "4. Топ-5 получают призы!\n\n"
        "🥇 1 место: 40% банка\n"
        "🥈 2 место: 25% банка\n"
        "🥉 3 место: 15% банка\n"
        "4-5 место: по 10%",
        parse_mode="HTML"
    )
    await callback.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
