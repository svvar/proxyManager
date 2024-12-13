from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

from database.operations.bot_operations import get_geos, add_geo, delete_geo
from bot.core.states import Geos

geo_router = Router()


@geo_router.message(F.text == 'Гео')
async def geos_menu(message: types.Message):
    geos = await get_geos()

    text = 'Гео\n\n' + '\n'.join(
        [f'{geo.geo_id}. {geo.name}' for geo in geos])

    kb = InlineKeyboardBuilder()
    kb.button(text='Додати', callback_data='add_geo')
    if geos:
        kb.button(text='Видалити', callback_data='remove_geo')

    kb.adjust(2)

    await message.answer(text, reply_markup=kb.as_markup())


@geo_router.callback_query(F.data == 'add_geo')
async def new_geo(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer('Введіть назву нового гео')
    await callback.answer()
    await state.set_state(Geos.new_geo_name)


@geo_router.message(Geos.new_geo_name)
async def save_geo(message: types.Message, state: FSMContext):
    await add_geo(message.text)

    await message.answer('Нове гео додано')
    await state.clear()


@geo_router.callback_query(F.data == 'remove_geo')
async def remove_geo(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer('Введіть ID гео, яке хочете видалити')
    await callback.answer()
    await state.set_state(Geos.del_geo_id)


@geo_router.message(Geos.del_geo_id)
async def delete_geo_by_id(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer('ID має бути числом')
        return

    await delete_geo(int(message.text))

    await message.answer('Гео видалене')
    await state.clear()
