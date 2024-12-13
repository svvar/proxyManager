from datetime import datetime

from aiogram import Router, types, F
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiohttp import ClientSession

from api.utils.ip_requests import get_http_proxy_ip_multitry, get_socks_proxy_ip, get_ip_info
from database.models import Sellers, Ports, ProxyTypes, Geos
from database.operations.bot_operations import (get_sellers, get_sellers_ports, get_geos, get_proxy_types,
                                                add_port, flip_port_status, add_port_ip_version, delete_port)
from bot.core.states import ShowPorts, NewPort, TurnOnOffPort
from bot.core.callbacks import InlinePageCallback
from database.operations.api_port_transactions import create_new_ip_info

port_router = Router()


def _paged_kb(page: int, total_pages: int, objects: list):
    kb = InlineKeyboardBuilder()

    objects_page_items = objects[page * 10:page * 10 + 10]

    for obj in objects_page_items:
        if isinstance(obj, Sellers):
            kb.button(text=obj.mark, callback_data=f'seller_{obj.seller_id}')
        elif isinstance(obj, Ports):
            kb.button(text=f'{obj.host}:{obj.socks_port}:{obj.http_port}:{obj.login}  {"🟢" if obj.is_active else "🔴"}',
                      callback_data=f'port_{obj.port_id}')
        elif isinstance(obj, ProxyTypes):
            kb.button(text=obj.name, callback_data=f'proxy_type_{obj.proxy_type_id}')
        elif isinstance(obj, Geos):
            kb.button(text=obj.name, callback_data=f'geo_{obj.geo_id}')
    kb.adjust(1)

    nav_row = []
    if page > 0:
        nav_row.append(types.InlineKeyboardButton(text='⬅️', callback_data=InlinePageCallback(direction='prev',
                                                                                               action='page').pack()))
    if total_pages > 0:
        nav_row.append(types.InlineKeyboardButton(text=f'{page+1}/{total_pages+1}', callback_data='nothing'))
    if page < total_pages:
        nav_row.append(types.InlineKeyboardButton(text='➡️', callback_data=InlinePageCallback(direction='next',
                                                                                               action='page').pack()))

    kb.row(*nav_row)
    return kb

def _split_message_by_newline(text: str, max_length: int = 4096) -> list:
    chunks = []
    while len(text) > max_length:
        split_index = text.rfind('\n', 0, max_length)
        if split_index == -1:
            split_index = max_length
        chunks.append(text[:split_index].strip())
        text = text[split_index:].lstrip('\n')
    if text:
        chunks.append(text.strip())
    return chunks


# @port_router.callback_query(InlinePageCallback.filter(F.action == 'page'), ShowPorts.choosing_seller)
# @port_router.callback_query(InlinePageCallback.filter(F.action == 'page'), NewPort.choosing_proxy_type)
# @port_router.callback_query(InlinePageCallback.filter(F.action == 'page'), NewPort.choosing_geo)
# @port_router.callback_query(InlinePageCallback.filter(F.action == 'page'), NewPort.choosing_seller)
@port_router.callback_query(InlinePageCallback.filter(F.action == 'page'))
async def inline_kb_switch_page(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()

    current_state = await state.get_state()
    if current_state == NewPort.choosing_proxy_type:
        page = data.get('types_page', 0)
        content = await get_proxy_types()
    elif current_state == NewPort.choosing_geo:
        page = data.get('geos_page', 0)
        content = await get_geos()
    elif current_state in (NewPort.choosing_seller, ShowPorts.choosing_seller, TurnOnOffPort.choosing_seller):
        page = data.get('sellers_page', 0)
        content = await get_sellers()
    elif current_state == TurnOnOffPort.choosing_port:
        page = data.get('ports_page', 0)
        content = await get_sellers_ports(data['seller_id'])

    total_pages = len(content) // 10
    callback_data = InlinePageCallback.unpack(callback.data)
    if callback_data.direction == 'next':
        page += 1
    else:
        page -= 1

    kb = _paged_kb(page, total_pages, content)

    if current_state == NewPort.choosing_proxy_type:
        await state.update_data(types_page=page)
    elif current_state == NewPort.choosing_geo:
        await state.update_data(geos_page=page)
    elif current_state in (NewPort.choosing_seller, ShowPorts.choosing_seller, TurnOnOffPort.choosing_seller):
        await state.update_data(sellers_page=page)
    elif current_state == TurnOnOffPort.choosing_port:
        await state.update_data(ports_page=page)
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=kb.as_markup())


@port_router.message(F.text == 'Керування портами')
async def ports_menu(message: types.Message):
    kb = ReplyKeyboardBuilder()
    kb.button(text='Переглянути порти')
    kb.button(text='Додати новий порт')
    kb.button(text='Вимкнути/увімкнути')
    kb.button(text='На головну')
    kb.adjust(2)

    await message.answer('Виберіть дію', reply_markup=kb.as_markup(resize_keyboard=True))




##############
# Show ports #
##############

@port_router.message(F.text == 'Переглянути порти')
async def show_ports(message: types.Message, state: FSMContext):
    sellers = await get_sellers()
    seller_pages = len(sellers) // 10

    await state.update_data(sellers_page=0)

    kb = _paged_kb(0, seller_pages, sellers)

    await message.answer('Виберіть селлера, порти якого ви хочете переглянути', reply_markup=kb.as_markup())
    await state.set_state(ShowPorts.choosing_seller)

@port_router.callback_query(ShowPorts.choosing_seller)
async def show_seller_ports(callback: types.CallbackQuery, state: FSMContext):
    seller_id = int(callback.data.split('_')[1])
    ports = await get_sellers_ports(seller_id)

    text = '\n'.join([f'{port.host} : {port.socks_port} : {port.http_port} : {port.login}'
                      f'  {"🟢" if port.is_active else "🔴"}' for port in ports])
    if not text:
        await callback.answer('У цього селлера немає доданих портів')
    text_chunks = _split_message_by_newline(text)
    for chunk in text_chunks:
        await callback.message.answer(chunk)

    await callback.answer()
    await state.clear()


################
# Add new port #
################


@port_router.message(F.text == 'Додати новий порт')
async def new_port_protocol(message: types.Message, state: FSMContext):
    # ip_version = int(callback.data)
    # await state.update_data(ip_version=ip_version)

    kb = InlineKeyboardBuilder()
    kb.button(text='SOCKS5', callback_data='socks')
    kb.button(text='HTTP', callback_data='http')
    kb.button(text='SOCKS5+HTTP', callback_data='socks+http')
    kb.adjust(1)

    await message.answer('Виберіть протокол проксі:', reply_markup=kb.as_markup())
    await state.set_state(NewPort.choosing_proxy_protocol)


@port_router.callback_query(NewPort.choosing_proxy_protocol)
async def new_port_type(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(protocol=callback.data)
    proxy_types = await get_proxy_types()

    types_pages = len(proxy_types) // 10
    await state.update_data(types_page=0)

    kb = _paged_kb(0, types_pages, proxy_types)

    await callback.answer()
    await callback.message.edit_text('Виберіть тип проксі:', reply_markup=kb.as_markup())
    await state.set_state(NewPort.choosing_proxy_type)


@port_router.callback_query(NewPort.choosing_proxy_type)
async def new_port_geo(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(proxy_type_id=int(callback.data.split('_')[-1]))

    geos = await get_geos()

    geos_pages = len(geos) // 10
    await state.update_data(geos_page=0)

    kb = _paged_kb(0, geos_pages, geos)

    await callback.answer()
    await callback.message.edit_text('Виберіть гео: ', reply_markup=kb.as_markup())
    await state.set_state(NewPort.choosing_geo)


@port_router.callback_query(NewPort.choosing_geo)
async def new_port_seller(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(geo_id=int(callback.data.split('_')[-1]))

    sellers = await get_sellers()

    sellers_pages = len(sellers) // 10
    await state.update_data(sellers_page=0)

    kb = _paged_kb(0, sellers_pages, sellers)

    await callback.answer()
    await callback.message.edit_text("Виберіть селлера: ", reply_markup=kb.as_markup())
    await state.set_state(NewPort.choosing_seller)


@port_router.callback_query(NewPort.choosing_seller)
async def new_port_rotation(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(seller_id=int(callback.data.split('_')[-1]))

    kb = InlineKeyboardBuilder()
    kb.button(text='Статичний', callback_data='STATIC')
    kb.button(text='За посиланням', callback_data='BY_LINK')
    kb.button(text='За фіксованим часом', callback_data='BY_TIME')
    kb.button(text='При кожному підключенні', callback_data='BY_CONNECTION')
    kb.adjust(1)

    await callback.answer()
    await callback.message.edit_text('Виберіть тип зміни IP:', reply_markup=kb.as_markup())
    await state.set_state(NewPort.choosing_rotation)


@port_router.callback_query(NewPort.choosing_rotation)
async def new_port_info_input(callback: types.CallbackQuery, state: FSMContext):
    rotation_type = callback.data
    await state.update_data(rotation_type=rotation_type)


    text = (f'*Введіть дані нового порту через пробіл:\n\nhost socks_port http_port login password rent_end'
            f'{" rotation_link" if rotation_type == "BY_LINK" else ""}\n\nвкажіть rent_end в форматі ДД.ММ.РРРР-гг:хх:сс*')

    await callback.answer()
    await callback.message.edit_text(text, parse_mode='Markdown', reply_markup=None)
    await state.set_state(NewPort.input_data)


@port_router.message(NewPort.input_data)
async def save_new_port(message: types.Message, state: FSMContext):
    stored_data = await state.get_data()
    proxy_protocol = stored_data['protocol']

    data = message.text.split()
    if stored_data['rotation_type'] == 'BY_LINK':
        if len(data) != 6:
            await message.answer('Невірна кількість аргументів. Введіть заново')
            return
    else:
        if len(data) != 5:
            await message.answer('Невірна кількість аргументів. Введіть заново')
            return

    host, socks_port, http_port, login, password, rent_end = data[:6]
    rotation_link = data[6] if len(data) == 7 else None

    try:
        rent_end = datetime.strptime(rent_end, '%d.%m.%Y-%H:%M:%S')
    except ValueError:
        await message.answer("Дата введена неправильно")
        text = (f'*Введіть дані нового порту через пробіл:\n\nhost socks_port http_port login password rent_end'
                f'{" rotation_link" if stored_data["rotation_type"] == "BY_LINK" else ""}\n\nвкажіть rent_end в форматі ДД.ММ.РРРР-гг:хх:сс*')

        await message.answer(text, parse_mode='Markdown', reply_markup=None)
        return

    data = {
        "proxy_type_id": stored_data['proxy_type_id'],
        "geo_id": stored_data['geo_id'],
        "host": host,
        "socks_port": socks_port,
        "http_port": http_port,
        "login": login,
        "password": password,
        "is_active": True,
        "rent_end": rent_end,
        "rotation_type": stored_data['rotation_type'],
        "rotation_link": rotation_link,
        "seller_id": stored_data['seller_id']
    }

    try:
        http_session = ClientSession()
        port_id = await add_port(data)
        # if proxy_protocol == 'http':
        ip, ip_ver = await get_http_proxy_ip_multitry(http_session, host, int(http_port), login, password)
        # else:
        #     ip, ip_ver = await get_socks_proxy_ip(host, port, login, password)

        if ip:
            await add_port_ip_version(port_id, ip_ver)
            ip_info = await get_ip_info(http_session, ip)
            await create_new_ip_info(port_id, ip_info['ip'], ip_ver, ip_info['city'], ip_info['region'],
                                     ip_info['org'])
        else:
            await delete_port(port_id)

        await message.answer('Порт доданий')
        await http_session.close()
    except Exception as e:
        print(e)
        await message.answer('Виникла помилка, почніть спочатку')
    await state.clear()
    await ports_menu(message)


################################
# Port activation/deactivation #
################################

@port_router.message(F.text == 'Вимкнути/увімкнути')
async def turn_port_start(message: types.Message, state: FSMContext):
    sellers = await get_sellers()
    seller_pages = len(sellers) // 10

    await state.update_data(seller_page=0)

    kb = _paged_kb(0, seller_pages, sellers)

    await message.answer('Виберіть селлера, порт якого ви хочете перемкнути', reply_markup=kb.as_markup())
    await state.set_state(TurnOnOffPort.choosing_seller)


@port_router.callback_query(TurnOnOffPort.choosing_seller)
async def turn_port_list_ports(callback: types.CallbackQuery, state: FSMContext):
    seller_id = int(callback.data.split('_')[-1])
    await state.update_data(seller_id=seller_id)

    ports = await get_sellers_ports(seller_id)

    kb = _paged_kb(0, len(ports) // 10, ports)
    await state.update_data(ports_page=0)

    await callback.answer()
    await callback.message.edit_text("Керуйте портами", reply_markup=kb.as_markup())
    await state.set_state(TurnOnOffPort.choosing_port)


@port_router.callback_query(TurnOnOffPort.choosing_port)
async def turn_port_change_status(callback: types.CallbackQuery, state: FSMContext):
    selected_port = int(callback.data.split('_')[-1])
    data = await state.get_data()

    flip_result = await flip_port_status(selected_port)
    ports = await get_sellers_ports(data['seller_id'])

    kb = _paged_kb(data['ports_page'], len(ports) // 10, ports)

    await callback.answer("Порт активовано" if flip_result else "Порт деактивовано")
    await callback.message.edit_reply_markup(reply_markup=kb.as_markup())

