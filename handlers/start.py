"""
handlers/start.py — стартовый обработчик и главное меню.

Обрабатывает:
  /start     — первый запуск бота
  /menu      — возврат в главное меню
  "🏠 Главное меню" — кнопка возврата
"""

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from keyboards import main_menu

router = Router()

WELCOME_TEXT = """
👋 Добро пожаловать в автосервис <b>«Починим и точка»</b>!

Мы занимаемся ремонтом и обслуживанием автомобилей.

Выберите, что вас интересует 👇
"""


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """
    Срабатывает на команду /start.
    state.clear() — сбрасываем любое активное состояние FSM,
    чтобы пользователь не застрял в середине диалога.
    """
    await state.clear()
    await message.answer(
        WELCOME_TEXT,
        parse_mode="HTML",
        reply_markup=main_menu()
    )


@router.message(Command("menu"))
@router.message(F.text == "🏠 Главное меню")
async def cmd_menu(message: Message, state: FSMContext):
    """Возврат в главное меню из любого места."""
    await state.clear()
    await message.answer(
        "Главное меню:",
        reply_markup=main_menu()
    )
