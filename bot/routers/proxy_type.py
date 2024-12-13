from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

from database.operations.bot_operations import get_proxy_types, add_proxy_type, delete_proxy_type
from bot.core.states import ProxyTypes


proxy_type_router = Router()


@proxy_type_router.message(F.text == 'Типи проксі')
async def proxy_types_menu(message: types.Message):
    proxy_types = await get_proxy_types()
    
    text = 'Типи проксі\n\n' + '\n'.join([f'{proxy_type.proxy_type_id}. {proxy_type.name}' for proxy_type in proxy_types])
    
    kb = InlineKeyboardBuilder()
    kb.button(text='Додати', callback_data='add_proxy_type')
    if proxy_types:
        kb.button(text='Видалити', callback_data='remove_proxy_type')
        
    kb.adjust(2)
    
    await message.answer(text, reply_markup=kb.as_markup())
    

@proxy_type_router.callback_query(F.data == 'add_proxy_type')
async def new_proxy_type(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer('Введіть назву нового типу проксі')
    await callback.answer()
    await state.set_state(ProxyTypes.new_type_name)
    
    
@proxy_type_router.message(ProxyTypes.new_type_name)
async def save_proxy_type(message: types.Message, state: FSMContext):
    await add_proxy_type(message.text)
    
    await message.answer('Тип проксі доданий')
    await state.clear()


@proxy_type_router.callback_query(F.data == 'remove_proxy_type')
async def remove_proxy_type(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer('Введіть ID типу проксі, який хочете видалити')
    await callback.answer()
    await state.set_state(ProxyTypes.del_type_id)
    
    
@proxy_type_router.message(ProxyTypes.del_type_id)
async def delete_proxy_type_by_id(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer('ID має бути числом')
        return
    
    await delete_proxy_type(int(message.text))
    
    await message.answer('Тип проксі видалений')
    await state.clear()
