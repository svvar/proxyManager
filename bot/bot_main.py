import os
from dotenv import load_dotenv, find_dotenv
from aiogram import Bot, Dispatcher, filters, types, F
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from bot.core.storage import db_session
from bot.routers.seller import seller_router
from bot.routers.statistics import statistics_router
from bot.routers.port import port_router

load_dotenv(find_dotenv())

BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)

dp = Dispatcher()


@dp.message(F.text == 'На головну')
@dp.message(filters.CommandStart())
async def start(message: types.Message):
    kb = ReplyKeyboardBuilder()
    kb.button(text='Керування портами')
    kb.button(text='Керування cеллерами')
    kb.button(text='Статистика')

    await message.answer('Я бот для керування портами проксі', reply_markup=kb.as_markup(resize_keyboard=True))


async def main():
    try:
        dp.include_router(seller_router)
        dp.include_router(statistics_router)
        dp.include_router(port_router)

        await dp.start_polling(bot)
    finally:
        await db_session.close()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
