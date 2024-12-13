from datetime import datetime, timedelta

from aiogram import Bot

from config import BOT_ADMINS
from database.operations.bot_operations import get_rent_end_times, get_port


async def rent_end_check(bot: Bot):
    text = ''
    rent_end_times = await get_rent_end_times()
    for port_id, rent_end in rent_end_times:
        diff = datetime.strptime(rent_end, '%Y-%m-%d %H:%M:%S') - datetime.now()
        if diff < timedelta(hours=12):
            port = await get_port(port_id)
            text += f'Оренда порту {port.host}:{port.http_port}:{port.socks_port} {port.login} закінчується {rent_end}\n'

    if text:
        for admin in BOT_ADMINS:
            try:
                await bot.send_message(admin, text)
            except Exception:
                pass
