"""
states.py — все состояния FSM бота.

BookingStates  — запись клиента (многошаговая анкета)
QuestionStates — вопрос мастеру
AdminStates    — состояния для действий администратора
"""

from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    # Шаг 1: выбор услуги (inline-кнопки)
    waiting_service  = State()
    # Шаг 2: имя клиента
    waiting_name     = State()
    # Шаг 3: телефон
    waiting_phone    = State()
    # Шаг 4: марка автомобиля
    waiting_car_brand = State()
    # Шаг 5: модель автомобиля
    waiting_car_model = State()
    # Шаг 6: год выпуска
    waiting_car_year  = State()
    # Шаг 7: VIN (можно пропустить)
    waiting_vin       = State()
    # Шаг 8: желаемая дата визита
    waiting_date      = State()
    # Шаг 9: желаемое время визита (inline-кнопки)
    waiting_time      = State()
    # Шаг 10: финальное подтверждение
    confirm           = State()


class QuestionStates(StatesGroup):
    # Ждём вопрос (текст или медиа)
    waiting_question = State()


class AdminStates(StatesGroup):
    # Ждём комментарий к заявке
    waiting_comment  = State()
    # Ждём ответ на вопрос мастеру
    waiting_answer   = State()
