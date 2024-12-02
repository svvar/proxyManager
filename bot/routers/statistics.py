from datetime import datetime, date, timedelta

from aiogram import Router, types, F
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

from bot.core.callbacks import InlinePageCallback
from bot.core.storage import db_session
from database.models import Sellers, Ports, ProxyTypes, Geos
from database.operations.bot_operations import get_sellers, get_sellers_ports

from bot.core.states import Statistics

statistics_router = Router()

def _paged_kb(page: int, total_pages: int, objects: list):
    kb = InlineKeyboardBuilder()

    objects_page_items = objects[page * 10:page * 10 + 10]

    for obj in objects_page_items:
        if isinstance(obj, Sellers):
            kb.button(text=obj.mark, callback_data=f'seller_{obj.seller_id}')
        elif isinstance(obj, Ports):
            kb.button(text=f'{obj.host}:{obj.socks_port or obj.http_port}:{obj.login}  {"🟢" if obj.is_active else "🔴"}',
                      callback_data=f'port_{obj.port_id}')
    kb.adjust(1)

    nav_row = []
    if page > 0:
        nav_row.append(types.InlineKeyboardButton(text='⬅️', callback_data=InlinePageCallback(direction='prev',
                                                                                               action='page').pack()))
    nav_row.append(types.InlineKeyboardButton(text=f'{page+1}/{total_pages}'))
    if page < total_pages:
        nav_row.append(types.InlineKeyboardButton(text='➡️', callback_data=InlinePageCallback(direction='next',
                                                                                               action='page').pack()))

    kb.row(*nav_row)
    return kb


@statistics_router.callback_query(InlinePageCallback.filter(F.action == 'page'))
async def inline_kb_switch_page(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()

    current_state = state.get_state()

    if current_state == Statistics.choosing_seller:
        page = data.get('sellers_page', 0)
        content = await get_sellers(db_session)
    elif current_state == Statistics.choosing_port:
        page = data.get('ports_page', 0)
        content = await get_sellers_ports(db_session, data['seller_id'])

    total_pages = len(content) // 10
    callback_data = InlinePageCallback.unpack(callback.data)
    if callback_data['direction'] == 'next':
        total_pages += 1
    else:
        total_pages -= 1

    kb = _paged_kb(page, total_pages, content)

    if current_state == Statistics.choosing_seller:
        await state.update_data(sellers_page=page)
    elif current_state == Statistics.choosing_port:
        await state.update_data(ports_page=page)
    await callback.answer()
    await callback.message.edit_caption(reply_markup=kb.as_markup())



@statistics_router.message(F.text == 'Статистика')
async def statistics_menu(message: types.Message, state: FSMContext):
    await message.answer("Виберіть селлера і порт щоб переглянути статистику по ньому")

    sellers = await get_sellers(db_session)
    seller_pages = len(sellers) // 10

    await state.update_data(sellers_page=0)

    kb = _paged_kb(0, seller_pages, sellers)
    await message.answer('Виберіть селлера, порти якого ви хочете переглянути', reply_markup=kb.as_markup())
    await state.set_state(Statistics.choosing_seller)


@statistics_router.callback_query(Statistics.choosing_seller)
async def select_port(callback: types.CallbackQuery, state: FSMContext):
    seller_id = int(callback.data.split('_')[-1])
    await state.update_data(seller_id=seller_id)

    ports = await get_sellers_ports(db_session, seller_id)

    kb = _paged_kb(0, len(ports) // 10, ports)
    await state.update_data(ports_page=0)

    await callback.answer()
    await callback.message.edit_text("Виберіть порт", reply_markup=kb.as_markup())


@statistics_router.callback_query(Statistics.choosing_port)
async def select_time_period(callback: types.CallbackQuery, state: FSMContext):
    port_id = int(callback.data.split('_')[-1])
    await state.update_data(port_id=port_id)

    kb = InlineKeyboardBuilder()
    kb.button(text='За сьогодні', callback_data='today')
    kb.button(text='За тиждень', callback_data='week')
    kb.button(text='За місяць', callback_data='month')
    kb.button(text='Свій діапазон', callback_data='custom')
    kb.adjust(1)

    await callback.answer()
    await callback.message.edit_text('Виберіть період', reply_markup=kb.as_markup())
    await state.set_state(Statistics.choosing_time_period)



@statistics_router.callback_query(Statistics.choosing_time_period, F.data == 'custom')
async def ask_date_range(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text('Введіть дату в форматі ДД.ММ.РРРР\nабо діапазон дат ДД.ММ.РРРР - ДД.ММ.РРРР')
    await state.set_state(Statistics.input_custom_period)


@statistics_router.message(Statistics.input_custom_period)
async def save_custom_period(message: types.Message, state: FSMContext):
    if '-' in message.text:
        start, end = message.text.split('-')
        start = datetime.strptime(start.strip(), '%d.%m.%Y')
        end = datetime.strptime(end.strip(), '%d.%m.%Y')
    else:
        start = end = datetime.strptime(message.text.strip(), '%d.%m.%Y')

    await state.update_data(start_date=start, end_date=end)
    await show_statistics(message, state)


@statistics_router.callback_query(Statistics.choosing_time_period)
async def save_date(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == 'today':
        start = end = date.today()
    elif callback.data == 'week':
        start = date.today()
        end = start - timedelta(days=7)
    elif callback.data == 'month':
        start = date.today()
        end = start - timedelta(days=30)

    await callback.answer()
    await state.update_data(start_date=start, end_date=end)
    await show_statistics(callback.message, state)


async def show_statistics(message: types.Message, state: FSMContext):
    data = await state.get_data()
    port_id = data['port_id']
    start = data['start_date']
    end = data['end_date']

    await message.answer(f'Статистика по порту {port_id} за період з {start} по {end}')

