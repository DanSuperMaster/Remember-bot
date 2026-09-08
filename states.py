from aiogram.fsm.state import State, StatesGroup


class User(StatesGroup):
    waiting_for_day = State()
    waiting_for_time = State()
    waiting_for_custom_time = State()
    waiting_for_repeat = State()
    waiting_for_custom_repeat = State()
    waiting_for_text = State()
    waiting_for_confirmation = State()
