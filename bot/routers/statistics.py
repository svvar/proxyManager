import io
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

import xlsxwriter
from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

from database.operations.bot_operations import count_requests, get_ports, get_busy_time_for_port
from bot.core.states import Statistics

statistics_router = Router()


@statistics_router.message(F.text == 'Статистика')
async def select_time_period(message: types.Message, state: FSMContext):
    kb = InlineKeyboardBuilder()
    kb.button(text='За сьогодні', callback_data='today')
    kb.button(text='За тиждень', callback_data='week')
    kb.button(text='За місяць', callback_data='month')
    kb.button(text='Свій діапазон', callback_data='custom')
    kb.adjust(1)

    await message.answer('Виберіть період', reply_markup=kb.as_markup())
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
        start = end = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=ZoneInfo('UTC'))
    elif callback.data == 'week':
        end = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=ZoneInfo('UTC'))
        start = end - timedelta(days=7)
    elif callback.data == 'month':
        end = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=ZoneInfo('UTC'))
        start = end - timedelta(days=30)

    await callback.answer()
    await state.update_data(start_date=start, end_date=end)
    await show_statistics(callback.message, state)


async def show_statistics(message: types.Message, state: FSMContext):
    data = await state.get_data()
    start = data['start_date']
    end = data['end_date']

    total_time_in_range = (end - start).total_seconds()

    requests = await count_requests(start, end)

    await message.answer(f'Загальний час: {total_time_in_range}\nКількість запитів: {requests}')
    await state.clear()
    all_ports = await get_ports()
    ports_data = {}
    for port in all_ports:
        busy_time = await get_busy_time_for_port(start, end, port.port_id)
        busy_time = int(busy_time)
        ports_data[port.port_id] = {"busy_time": seconds_to_time(busy_time),
                                    "free_time": seconds_to_time(total_time_in_range - busy_time),
                                    "host": port.host,
                                    "http_port": port.http_port,
                                    "socks_port": port.socks_port}

    buffer = write_statistics_to_xlsx(f"{start.strftime('%d.%m.%Y')} - {end.strftime('%d.%m.%Y')}", requests, ports_data)
    input_file = types.BufferedInputFile(buffer.getvalue(), filename='statistics.xlsx')
    await message.answer_document(input_file)
    await state.clear()


def write_statistics_to_xlsx(date_range: str, requests:int, ports_data: dict):
    buffer = io.BytesIO()
    buffer.name = 'statistics.xlsx'

    workbook = xlsxwriter.Workbook(buffer)
    worksheet = workbook.add_worksheet()

    head_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 14,'bold': True})
    bold_table_head_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bg_color': '#e3e538', 'border': 2, 'font_size': 12, 'bold': True})
    normal_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'font_size': 12})

    worksheet.merge_range('A1:F2', f'Статистика за {date_range}', head_format)
    worksheet.merge_range('B4:C4', 'Кількість запитів', bold_table_head_format)
    worksheet.write('D4', requests, bold_table_head_format)

    worksheet.merge_range('A6:D6', 'Порт', bold_table_head_format)
    worksheet.merge_range('E6:E7', 'Час роботи', bold_table_head_format)
    worksheet.merge_range('F6:F7', 'Час простою', bold_table_head_format)
    worksheet.write('A7', 'ID', bold_table_head_format)
    worksheet.write('B7', 'Хост', bold_table_head_format)
    worksheet.write('C7', 'HTTP порт', bold_table_head_format)
    worksheet.write('D7', 'SOCKS порт', bold_table_head_format)

    for row, port_id in enumerate(ports_data.keys(), start=8):
        worksheet.write(f'A{row}', port_id, normal_format)
        worksheet.write(f'B{row}', ports_data[port_id]['host'], normal_format)
        worksheet.write(f'C{row}', ports_data[port_id]['http_port'], normal_format)
        worksheet.write(f'D{row}', ports_data[port_id]['socks_port'], normal_format)
        worksheet.write(f'E{row}', ports_data[port_id]['busy_time'], normal_format)
        worksheet.write(f'F{row}', ports_data[port_id]['free_time'], normal_format)

    worksheet.autofit()
    worksheet.set_column('A:A', width=8)
    workbook.close()

    return buffer


def seconds_to_time(input_seconds: int):
    hours, remainder = divmod(input_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    text = ""
    if hours:
        text += f"{hours}г "
    if minutes:
        text += f"{minutes}хв "
    if seconds:
        text += f"{seconds}с"
    if not input_seconds:
        text = "0с"

    return text



