from aiogram.filters.callback_data import CallbackData

class InlinePageCallback(CallbackData, prefix='sellers_pg'):
    direction: str
    action: str