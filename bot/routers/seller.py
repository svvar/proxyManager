from aiogram import Router, types, F
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext

from database.operations.bot_operations import get_ports, get_sellers, add_seller, delete_seller, get_seller
from bot.core.states import SellerStates
from bot.core.storage import db_session


seller_router = Router()


@seller_router.message(F.text == 'Керування cеллерами')
async def sellers_menu(message: types.Message):
    kb = ReplyKeyboardBuilder()
    kb.button(text='Переглянути селлерів')
    kb.button(text='Додати нового селлера')
    kb.button(text='Видалити селлера')
    kb.button(text='Переглянути порти селлера')
    kb.button(text='На головну')
    kb.adjust(2)

    await message.answer('Виберіть дію', reply_markup=kb.as_markup(resize_keyboard=True))


@seller_router.message(F.text == 'Переглянути селлерів')
async def show_sellers(message: types.Message):
    sellers = await get_sellers(db_session)
    if not sellers:
        await message.answer('Список селлерів порожній')
        return

    await message.answer('\n\n'.join([f'ID: {seller.seller_id}\nMark: {seller.mark}\nLogin: {seller.login}\n'
                                      f'Password: {seller.password}\nSite:{seller.site_link}' for seller in sellers]))



@seller_router.message(F.text == 'Додати нового селлера')
async def new_seller(message: types.Message, state: FSMContext):
    await message.answer('Введіть дані нового селлера через пробіл: mark login password site_link')
    await state.set_state(SellerStates.seller_add_input)


@seller_router.message(SellerStates.seller_add_input)
async def save_seller(message: types.Message, state: FSMContext):
    mark, login, password, site_link = message.text.split()
    await add_seller(db_session, mark, login, password, site_link)

    await message.answer('Селлер доданий')
    await state.clear()
    await sellers_menu(message)


@seller_router.message(F.text == 'Видалити селлера')
async def remove_seller(message: types.Message, state: FSMContext):
    await show_sellers(message)
    await message.answer('Введіть ID селлера, якого хочете видалити')
    await state.set_state(SellerStates.seller_remove_input)


@seller_router.message(SellerStates.seller_remove_input)
async def remove_seller_db(message: types.Message, state: FSMContext):
    seller_id = int(message.text)
    result = await delete_seller(db_session, seller_id)

    if result:
        await message.answer('Селлер видалений')
    else:
        await message.answer('Селлера з таким ID не знайдено')

    await state.clear()
    await sellers_menu(message)


# @seller_router.message(F.text == 'Переглянути порти селлера')
# async def show_seller_ports(message: types.Message, state: FSMContext):
#     await show_sellers(message)
#     await message.answer('Введіть ID селлера, порти якого хочете переглянути')
#     await state.set_state(SellerStates.seller_show_ports)
#
#
# @seller_router.message(SellerStates.seller_show_ports)
# async def show_ports(message: types.Message, state: FSMContext):
    # seller_id = int(message.text)
    # seller = await get_sellers(db_session)
    #
    # ports = seller.