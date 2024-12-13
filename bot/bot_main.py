from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot, Dispatcher, filters, types, F
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from config import TG_BOT_TOKEN
from bot.core.middlewares import AccessMiddleware
from bot.routers.seller import seller_router
from bot.routers.statistics import statistics_router
from bot.routers.port import port_router
from bot.routers.geo import geo_router
from bot.routers.proxy_type import proxy_type_router
from bot.routers.synchronization import sync_router
from bot.core.tasks import rent_end_check


bot = Bot(token=TG_BOT_TOKEN)

dp = Dispatcher()
scheduler = AsyncIOScheduler()


@dp.message(F.text == 'На головну')
@dp.message(filters.CommandStart())
async def start(message: types.Message):
    kb = ReplyKeyboardBuilder()
    kb.button(text='Керування портами')
    kb.button(text='Керування cеллерами')
    kb.button(text='Типи проксі')
    kb.button(text='Гео')
    kb.button(text='Статистика')
    kb.button(text='Синхронізація')
    kb.adjust(2)

    await message.answer('Я бот для керування портами проксі', reply_markup=kb.as_markup(resize_keyboard=True))


async def start_bot():
    dp.message.middleware(AccessMiddleware())
    dp.include_router(seller_router)
    dp.include_router(statistics_router)
    dp.include_router(port_router)
    dp.include_router(geo_router)
    dp.include_router(proxy_type_router)
    dp.include_router(sync_router)

    scheduler.add_job(rent_end_check, 'interval', hours=6, args=[bot])
    scheduler.start()

    await dp.start_polling(bot)

