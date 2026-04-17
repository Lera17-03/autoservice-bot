"""
handlers/booking.py — FSM-запись клиента.

ИЗМЕНЕНИЯ по телефону:
  Вместо ручного ввода — кнопка «📱 Поделиться номером».
  Telegram автоматически передаёт номер телефона пользователя.
  Также оставлена возможность ввести номер вручную (на случай если
  пользователь хочет указать другой номер).

  KeyboardButton(request_contact=True) — стандартный механизм Telegram,
  который показывает системный диалог «Разрешить боту видеть мой номер?».
  После согласия бот получает message.contact с phone_number внутри.

  Администратору в уведомлении теперь приходит:
    — имя в Telegram
    — @username (если есть)
    — номер телефона
    — ссылка tg://user?id=XXX для быстрого открытия чата
"""

from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove,
)
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from states import BookingStates
from keyboards import (
    services_keyboard, get_service_name,
    cancel_keyboard, skip_cancel_keyboard,
    time_keyboard, confirm_keyboard, main_menu,
    BOOKING_STATUSES, admin_booking_keyboard,
)
from database.db import add_booking
from config import ADMIN_ID

router = Router()


# ─── КЛАВИАТУРА ДЛЯ ЗАПРОСА КОНТАКТА ─────────────────────

def contact_keyboard() -> ReplyKeyboardMarkup:
    """
    ReplyKeyboard с кнопкой «Поделиться номером».
    request_contact=True — Telegram покажет системный диалог подтверждения.
    После согласия пользователя бот получит его настоящий номер.
    Кнопка «Ввести вручную» позволяет написать любой другой номер.
    """
    builder = ReplyKeyboardBuilder()
    builder.button(text="📱 Поделиться номером", request_contact=True)
    builder.button(text="✏️ Ввести вручную")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


# ─── ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ──────────────────────────────

def booking_summary(data: dict) -> str:
    vin_line = f"🔑 VIN: <b>{data['vin']}</b>\n" if data.get("vin") else ""
    return (
        f"📋 <b>Проверьте вашу заявку:</b>\n\n"
        f"🔧 Услуга: <b>{data['service']}</b>\n"
        f"👤 Имя: <b>{data['name']}</b>\n"
        f"📞 Телефон: <b>{data['phone']}</b>\n\n"
        f"🚗 Автомобиль: <b>{data['car_brand']} {data['car_model']} ({data['car_year']})</b>\n"
        f"{vin_line}"
        f"\n📅 Дата визита: <b>{data['visit_date']}</b>\n"
        f"🕐 Время: <b>{data['visit_time']}</b>\n\n"
        f"Всё верно?"
    )


def admin_booking_text(data: dict, booking_id: int) -> str:
    vin_line = f"🔑 VIN: {data['vin']}\n" if data.get("vin") else ""
    username = data.get("username") or ""
    user_id  = data["user_id"]
    # Ссылка для быстрого открытия чата с клиентом
    tg_link  = f'<a href="tg://user?id={user_id}">открыть чат</a>'
    username_str = f"@{username}  " if username else ""
    return (
        f"🔔 <b>Новая заявка №{booking_id}!</b>\n\n"
        f"🔧 Услуга: {data['service']}\n"
        f"👤 Имя: {data['name']}\n"
        f"📞 Телефон: {data['phone']}\n\n"
        f"🚗 {data['car_brand']} {data['car_model']} ({data['car_year']})\n"
        f"{vin_line}"
        f"📅 Дата: {data['visit_date']}  🕐 {data['visit_time']}\n\n"
        f"👤 Клиент: {username_str}{tg_link}  (ID: {user_id})"
    )


# ─── ШАГ 0: "Записаться" ──────────────────────────────────

@router.message(F.text == "📋 Записаться")
async def start_booking(message: Message, state: FSMContext):
    await state.set_state(BookingStates.waiting_service)
    await message.answer(
        "🔧 <b>Выберите услугу:</b>",
        parse_mode="HTML",
        reply_markup=services_keyboard()
    )


# ─── ШАГ 1: Услуга ────────────────────────────────────────

@router.callback_query(BookingStates.waiting_service, F.data.startswith("service_"))
async def choose_service(callback: CallbackQuery, state: FSMContext):
    service_name = get_service_name(callback.data)
    await state.update_data(service=service_name)
    await state.set_state(BookingStates.waiting_name)
    await callback.answer()
    await callback.message.edit_text(
        f"✅ Услуга: <b>{service_name}</b>\n\n"
        f"👤 Введите ваше <b>имя</b>:",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )


# ─── ШАГ 2: Имя ───────────────────────────────────────────

@router.message(BookingStates.waiting_name, F.text)
async def enter_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("⚠️ Слишком короткое имя. Попробуйте ещё раз:", reply_markup=cancel_keyboard())
        return
    await state.update_data(name=name)
    await state.set_state(BookingStates.waiting_phone)
    # Показываем кнопку «Поделиться номером»
    await message.answer(
        f"👤 Имя: <b>{name}</b>\n\n"
        f"📞 <b>Укажите номер телефона:</b>\n\n"
        f"Нажмите кнопку ниже — Telegram автоматически передаст ваш номер.\n"
        f"Или введите любой другой номер вручную.",
        parse_mode="HTML",
        reply_markup=contact_keyboard()
    )


# ─── ШАГ 3а: Телефон через кнопку «Поделиться» ───────────

@router.message(BookingStates.waiting_phone, F.contact)
async def receive_contact(message: Message, state: FSMContext):
    """
    Telegram присылает объект message.contact когда пользователь
    нажал кнопку «Поделиться номером» и подтвердил.
    phone_number всегда в формате +71234567890.
    """
    phone = message.contact.phone_number
    # Добавляем + если его нет
    if not phone.startswith("+"):
        phone = "+" + phone

    await state.update_data(phone=phone)
    await _ask_car_brand(message, state, phone)


# ─── ШАГ 3б: Пользователь нажал «Ввести вручную» ─────────

@router.message(BookingStates.waiting_phone, F.text == "✏️ Ввести вручную")
async def phone_manual_prompt(message: Message):
    """Просим написать номер текстом."""
    from keyboards import cancel_keyboard as ck
    await message.answer(
        "✏️ Введите номер телефона:\n<i>Например: +7 900 123-45-67</i>",
        parse_mode="HTML",
        reply_markup=ck()
    )


# ─── ШАГ 3в: Телефон введён текстом ──────────────────────

@router.message(BookingStates.waiting_phone, F.text)
async def enter_phone_text(message: Message, state: FSMContext):
    phone = message.text.strip()
    if len(''.join(filter(str.isdigit, phone))) < 10:
        await message.answer("⚠️ Неверный формат. Введите телефон ещё раз:")
        return
    await state.update_data(phone=phone)
    await _ask_car_brand(message, state, phone)


# ─── Вспомогательная: следующий шаг после телефона ───────

async def _ask_car_brand(message: Message, state: FSMContext, phone: str):
    """Убираем клавиатуру с кнопкой контакта и переходим к авто."""
    await state.set_state(BookingStates.waiting_car_brand)
    await message.answer(
        f"📞 Телефон: <b>{phone}</b>\n\n"
        f"🚗 Введите <b>марку автомобиля</b>:\n<i>Например: Toyota, BMW, Lada</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()  # убираем кнопку «Поделиться»
    )
    # Показываем inline-кнопку «Отмена»
    await message.answer("", reply_markup=cancel_keyboard())


# ─── ШАГ 4: Марка ─────────────────────────────────────────

@router.message(BookingStates.waiting_car_brand, F.text)
async def enter_car_brand(message: Message, state: FSMContext):
    brand = message.text.strip()
    if len(brand) < 2:
        await message.answer("⚠️ Введите марку автомобиля:", reply_markup=cancel_keyboard())
        return
    await state.update_data(car_brand=brand)
    await state.set_state(BookingStates.waiting_car_model)
    await message.answer(
        f"🚗 Марка: <b>{brand}</b>\n\n"
        f"📝 Введите <b>модель</b>:\n<i>Например: Camry, X5, Vesta</i>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )


# ─── ШАГ 5: Модель ────────────────────────────────────────

@router.message(BookingStates.waiting_car_model, F.text)
async def enter_car_model(message: Message, state: FSMContext):
    model = message.text.strip()
    await state.update_data(car_model=model)
    await state.set_state(BookingStates.waiting_car_year)
    await message.answer(
        f"📝 Модель: <b>{model}</b>\n\n"
        f"📅 Введите <b>год выпуска</b>:\n<i>Например: 2019</i>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )


# ─── ШАГ 6: Год ───────────────────────────────────────────

@router.message(BookingStates.waiting_car_year, F.text)
async def enter_car_year(message: Message, state: FSMContext):
    year = message.text.strip()
    if not year.isdigit() or not (1970 <= int(year) <= 2030):
        await message.answer("⚠️ Введите корректный год (например: 2018):", reply_markup=cancel_keyboard())
        return
    await state.update_data(car_year=year)
    await state.set_state(BookingStates.waiting_vin)
    await message.answer(
        f"📅 Год: <b>{year}</b>\n\n"
        f"🔑 Введите <b>VIN-код</b> (необязательно):\n"
        f"<i>Если не знаете — нажмите «Пропустить».</i>",
        parse_mode="HTML",
        reply_markup=skip_cancel_keyboard("skip_vin")
    )


# ─── ШАГ 7: VIN ───────────────────────────────────────────

@router.callback_query(BookingStates.waiting_vin, F.data == "skip_vin")
async def skip_vin(callback: CallbackQuery, state: FSMContext):
    await state.update_data(vin="")
    await state.set_state(BookingStates.waiting_date)
    await callback.answer()
    await callback.message.edit_text(
        f"🔑 VIN: <i>не указан</i>\n\n"
        f"📅 Введите <b>желаемую дату визита</b>:\n<i>Например: 20.07.2025</i>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )


@router.message(BookingStates.waiting_vin, F.text)
async def enter_vin(message: Message, state: FSMContext):
    vin = message.text.strip().upper()
    await state.update_data(vin=vin)
    await state.set_state(BookingStates.waiting_date)
    await message.answer(
        f"🔑 VIN: <b>{vin}</b>\n\n"
        f"📅 Введите <b>желаемую дату визита</b>:\n<i>Например: 20.07.2025</i>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )


# ─── ШАГ 8: Дата ──────────────────────────────────────────

@router.message(BookingStates.waiting_date, F.text)
async def enter_date(message: Message, state: FSMContext):
    date = message.text.strip()
    await state.update_data(visit_date=date)
    await state.set_state(BookingStates.waiting_time)
    await message.answer(
        f"📅 Дата: <b>{date}</b>\n\n"
        f"🕐 Выберите <b>удобное время</b>:",
        parse_mode="HTML",
        reply_markup=time_keyboard()
    )


# ─── ШАГ 9а: Время — кнопка ──────────────────────────────

@router.callback_query(BookingStates.waiting_time, F.data.startswith("time_") & ~F.data.in_({"time_custom"}))
async def choose_time(callback: CallbackQuery, state: FSMContext):
    time_value = callback.data.replace("time_", "")
    await state.update_data(visit_time=time_value)
    data = await state.get_data()
    await state.set_state(BookingStates.confirm)
    await callback.answer()
    await callback.message.edit_text(
        booking_summary(data),
        parse_mode="HTML",
        reply_markup=confirm_keyboard()
    )


# ─── ШАГ 9б: Время — своё ────────────────────────────────

@router.callback_query(BookingStates.waiting_time, F.data == "time_custom")
async def time_custom_prompt(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "✏️ Введите удобное вам время:\n<i>Например: 08:30</i>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )


@router.message(BookingStates.waiting_time, F.text)
async def enter_custom_time(message: Message, state: FSMContext):
    time_value = message.text.strip()
    await state.update_data(visit_time=time_value)
    data = await state.get_data()
    await state.set_state(BookingStates.confirm)
    await message.answer(
        booking_summary(data),
        parse_mode="HTML",
        reply_markup=confirm_keyboard()
    )


# ─── ШАГ 10: ПОДТВЕРЖДЕНИЕ ────────────────────────────────

@router.callback_query(StateFilter(BookingStates.confirm), F.data == "confirm_booking")
async def confirm_booking(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    booking_id = await add_booking(
        user_id=callback.from_user.id,
        username=callback.from_user.username or "",
        service=data["service"],
        name=data["name"],
        phone=data["phone"],
        car_brand=data["car_brand"],
        car_model=data["car_model"],
        car_year=data["car_year"],
        vin=data.get("vin", ""),
        visit_date=data["visit_date"],
        visit_time=data["visit_time"],
    )

    await state.clear()

    await callback.answer("✅ Заявка принята!")
    await callback.message.edit_text(
        f"🎉 <b>Заявка принята!</b>\n\n"
        f"Мы свяжемся с вами по номеру <b>{data['phone']}</b>.\n"
        f"📅 Записаны на: <b>{data['visit_date']}</b> в <b>{data['visit_time']}</b>\n\n"
        f"Спасибо, что выбрали нас! 🚗",
        parse_mode="HTML"
    )
    await callback.message.answer("Главное меню:", reply_markup=main_menu())

    data["user_id"] = callback.from_user.id
    data["username"] = callback.from_user.username or ""
    try:
        await callback.bot.send_message(
            ADMIN_ID,
            admin_booking_text(data, booking_id),
            parse_mode="HTML",
            reply_markup=admin_booking_keyboard(booking_id)
        )
    except Exception:
        pass


# ─── ОТМЕНА — всегда после confirm_booking ───────────────

@router.callback_query(F.data == "cancel_booking")
async def cancel_booking(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Отменено")
    await callback.message.edit_text("❌ Запись отменена.")
    await callback.message.answer("Главное меню:", reply_markup=main_menu())


# ─── МОИ ЗАПИСИ ───────────────────────────────────────────

@router.message(F.text == "📄 Мои записи")
async def my_bookings(message: Message):
    from database.db import get_user_bookings
    bookings = await get_user_bookings(message.from_user.id)

    if not bookings:
        await message.answer(
            "📭 У вас пока нет записей.\n\nНажмите <b>«Записаться»</b> чтобы создать заявку.",
            parse_mode="HTML",
            reply_markup=main_menu()
        )
        return

    text = "📋 <b>Ваши записи:</b>\n\n"
    for b in bookings:
        status_label = BOOKING_STATUSES.get(b["status"], b["status"])
        comment_line = f"\n💬 <i>{b['comment']}</i>" if b.get("comment") else ""
        vin_line = f"\n🔑 VIN: {b['vin']}" if b.get("vin") else ""
        text += (
            f"{status_label}\n"
            f"🔧 {b['service']}\n"
            f"🚗 {b.get('car_brand','')} {b.get('car_model','')} ({b.get('car_year','')})"
            f"{vin_line}\n"
            f"📅 {b.get('visit_date','')}  🕐 {b.get('visit_time','')}"
            f"{comment_line}\n"
            f"{'─' * 22}\n"
        )

    await message.answer(text, parse_mode="HTML", reply_markup=main_menu())
