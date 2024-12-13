from aiogram import Router, F, types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.operations.website_sync_operations import autosync_on, autosync_off, get_sync_status

sync_router = Router()


@sync_router.message(F.text == 'Синхронізація')
async def toggle_synchronization(message: types.Message):
    status = await get_sync_status()
    if status:
        text = 'Сихронізація портів із сайтами селлерів *увімкнена* 🟢'
    else:
        text = 'Сихронізація портів із сайтами селлерів *вимкнена* 🔴'
    kb = InlineKeyboardBuilder()
    if status:
        kb.button(text='Вимкнути автосинхронізацію', callback_data='autosync_off')
    else:
        kb.button(text='Увімкнути автосинхронізацію', callback_data='autosync_on')

    await message.answer(text, reply_markup=kb.as_markup(resize_keyboard=True), parse_mode='Markdown')


@sync_router.callback_query(F.data == 'autosync_on')
async def autosync_on_callback(callback: types.CallbackQuery):
    await autosync_on()
    await callback.answer('Автосинхронізацію увімкнено')
    kb = InlineKeyboardBuilder()
    kb.button(text='Вимкнути автосинхронізацію', callback_data='autosync_off')
    await callback.message.edit_text('Сихронізація портів із сайтами селлерів *увімкнена* 🟢',
                                     parse_mode='Markdown',
                                     reply_markup=kb.as_markup(resize_keyboard=True))


@sync_router.callback_query(F.data == 'autosync_off')
async def autosync_off_callback(callback: types.CallbackQuery):
    await autosync_off()
    await callback.answer('Автосинхронізацію вимкнено')
    kb = InlineKeyboardBuilder()
    kb.button(text='Увімкнути автосинхронізацію', callback_data='autosync_on')
    await callback.message.edit_text('Сихронізація портів із сайтами селлерів *вимкнена* 🔴',
                                     parse_mode='Markdown',
                                     reply_markup=kb.as_markup(resize_keyboard=True))
