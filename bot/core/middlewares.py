from aiogram.dispatcher.middlewares.base import BaseMiddleware

from config import BOT_ADMINS


class AccessMiddleware(BaseMiddleware):
    """
    Middleware for checking access rights to the bot.
    """

    def __init__(self):
        super().__init__()

    async def __call__(self, handler, event, data):
        if event.from_user.id not in BOT_ADMINS:
            return await event.answer('Вы не можете использовать этого бота')
        return await handler(event, data)
