"""
keyboards.py — все клавиатуры бота.

Правило: одна функция = одна клавиатура.
Все данные для callback передаются через callback_data.
"""

from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


# ─── ГЛАВНОЕ МЕНЮ ─────────────────────────────────────────

def main_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="📋 Записаться")
    builder.button(text="💰 Узнать стоимость")
    builder.button(text="🎁 Акции")
    builder.button(text="📞 Контакты")
    builder.button(text="📄 Мои записи")
    builder.button(text="❓ Вопрос мастеру")
    builder.adjust(2, 2, 2)
    return builder.as_markup(resize_keyboard=True)


# ─── ВЫБОР УСЛУГИ ─────────────────────────────────────────

SERVICES = [
    ("🔧 Шиномонтаж",        "service_tire"),
    ("🛢 ТО / Замена масла",  "service_to"),
    ("🔍 Диагностика",        "service_diag"),
    ("🚗 Ходовая часть",      "service_suspension"),
    ("⚙️ Двигатель",          "service_engine"),
    ("🔩 Коробка передач",    "service_gearbox"),
    ("⚡️ Электрика",         "service_electric"),
]

SERVICE_NAMES = {cb: name for name, cb in SERVICES}


def services_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for text, cb in SERVICES:
        builder.button(text=text, callback_data=cb)
    builder.button(text="❌ Отмена", callback_data="cancel_booking")
    builder.adjust(1)
    return builder.as_markup()


def get_service_name(callback_data: str) -> str:
    return SERVICE_NAMES.get(callback_data, callback_data)


# ─── ПРОПУСТИТЬ ШАГ ───────────────────────────────────────

def skip_cancel_keyboard(skip_data: str = "skip") -> InlineKeyboardMarkup:
    """Кнопки 'Пропустить' и 'Отмена' — для необязательных шагов."""
    builder = InlineKeyboardBuilder()
    builder.button(text="➡️ Пропустить", callback_data=skip_data)
    builder.button(text="❌ Отмена",      callback_data="cancel_booking")
    builder.adjust(2)
    return builder.as_markup()


def cancel_keyboard() -> InlineKeyboardMarkup:
    """Только кнопка 'Отмена' — для обязательных шагов ввода текста."""
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel_booking")
    return builder.as_markup()


# ─── ВЫБОР ВРЕМЕНИ ────────────────────────────────────────

TIME_SLOTS = [
    "10:00", "11:00", "12:00", "13:00",
    "14:00", "15:00", "16:00", "17:00",
    "18:00", "19:00", "20:00", "21:00",
]


def time_keyboard() -> InlineKeyboardMarkup:
    """Слоты времени 10:00–21:00 + кнопки 'Своё время' и 'Отмена'."""
    builder = InlineKeyboardBuilder()
    for t in TIME_SLOTS:
        builder.button(text=t, callback_data=f"time_{t}")
    builder.button(text="✏️ Ввести своё время", callback_data="time_custom")
    builder.button(text="❌ Отмена",             callback_data="cancel_booking")
    builder.adjust(4, 4, 4, 1, 1)
    return builder.as_markup()


# ─── ПОДТВЕРЖДЕНИЕ ЗАПИСИ ─────────────────────────────────

def confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data="confirm_booking")
    builder.button(text="❌ Отменить",    callback_data="cancel_booking")
    builder.adjust(2)
    return builder.as_markup()


# ─── КНОПКА НАЗАД В МЕНЮ ──────────────────────────────────

def back_to_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="🏠 Главное меню")
    return builder.as_markup(resize_keyboard=True)


# ─── АДМИН: УПРАВЛЕНИЕ ЗАЯВКОЙ ────────────────────────────

# Новые статусы согласно ТЗ
BOOKING_STATUSES = {
    "pending":   "⏳ Ожидает подтверждения",
    "confirmed": "✅ Подтверждено",
    "in_work":   "🔨 В работе",
    "done":      "🏁 Завершено",
}


def admin_booking_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    """
    Кнопки управления заявкой для администратора:
    — 4 статуса
    — добавить/изменить комментарий
    """
    builder = InlineKeyboardBuilder()
    for status_key, label in BOOKING_STATUSES.items():
        builder.button(
            text=label,
            callback_data=f"set_status:{status_key}:{booking_id}"
        )
    builder.button(
        text="💬 Добавить комментарий",
        callback_data=f"add_comment:{booking_id}"
    )
    builder.adjust(1)
    return builder.as_markup()


# ─── АДМИН: ОТВЕТ НА ВОПРОС ───────────────────────────────

def admin_answer_keyboard(question_id: int) -> InlineKeyboardMarkup:
    """Кнопка 'Ответить' под каждым вопросом."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text="✍️ Ответить",
        callback_data=f"answer_question:{question_id}"
    )
    return builder.as_markup()
