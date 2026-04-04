import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import WebAppInfo, LabeledPrice
from aiogram.filters import Command
from aiogram.enums import ContentType

BOT_TOKEN = "7719717032:AAG4GwZp_2CRecHJ4mrsKKSIntgUsgqggEk"
WEB_APP_URL = "https://tap-wars.onrender.com/"  # URL где хостится фронтенд

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: types.Message):
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(
                text="🎮 Играть в Tap Wars",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )]
        ]
    )
    
    await message.answer(
        "⚡ Добро пожаловать в Tap Wars!\n\n"
        "👥 50 игроков\n"
        "⏱️ 60 секунд\n"
        "🏆 Топ-5 делят 2000⭐\n\n"
        "🎫 Билет стоит 50 ⭐\n\n"
        "Нажми на кнопку ниже, чтобы начать!",
        reply_markup=keyboard
    )

# Обработка предоплаты
@dp.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_q: types.PreCheckoutQuery):
    await pre_checkout_q.answer(ok=True)

# Обработка успешного платежа
@dp.message(lambda message: message.successful_payment is not None)
async def successful_payment_handler(message: types.Message):
    payment = message.successful_payment
    await message.answer(
        f"✅ Оплата прошла успешно!\n\n"
        f"💰 Списано: {payment.total_amount} ⭐\n"
        f"🎫 Билет активирован!\n\n"
        f"Жди начала игры!"
    )

async def main():
    print("🤖 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
