from aiogram.fsm.state import State, StatesGroup


class SellerStates(StatesGroup):
    seller_add_input = State()
    seller_remove_input = State()
    seller_show_ports = State()


class ShowPorts(StatesGroup):
    choosing_seller = State()


class NewPort(StatesGroup):
    # choosing_ip_version = State()
    choosing_proxy_protocol = State()
    choosing_proxy_type = State()
    choosing_geo = State()
    choosing_seller = State()
    choosing_rotation = State()
    input_data = State()


class TurnOnOffPort(StatesGroup):
    choosing_seller = State()
    choosing_port = State()


class Statistics(StatesGroup):
    choosing_seller = State()
    choosing_port = State()
    choosing_time_period = State()
    input_custom_period = State()


class ProxyTypes(StatesGroup):
    new_type_name = State()
    del_type_id = State()


class Geos(StatesGroup):
    new_geo_name = State()
    del_geo_id = State()


