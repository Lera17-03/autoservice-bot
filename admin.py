"""
handlers/admin.py — панель администратора.

Новые возможности:
  — 4 статуса заявки: pending / confirmed / in_work / done
  — Добавление комментария к заявке (FSM: AdminStates.waiting_comment)
  — Ответ на вопрос мастеру    (FSM: AdminStates.waiting_answer)
  — При смене статуса клиент получает уведомление с комментарием если он есть

Все хендлеры защищены фильтром IsAdmin — работают только для ADMIN_ID.
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, BaseFilter
from aiogram.fsm.context import FSMContext

from config import ADMIN_ID
from keyboards import admin_booking_keyboard, admin_answer_keyboard, BOOKING_STATUSES, main_menu
from states import AdminStates
from database.db import (
    get_all_bookings, get_booking_by_id,
    update_booking_status, update_booking_comment,
    get_question_by_id, save_answer,
)

router = Router()


# ─── ФИЛЬТР: только администратор ─────────────────────────

class IsAdmin(BaseFilter):
    async def __call__(self, event) -> bool:
        # Работает и для Message, и для CallbackQuery
        user = getattr(event, "from_user", None)
        return user is not None and user.id == ADMIN_ID


router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


# ─── ПАНЕЛЬ АДМИНИСТРАТОРА ────────────────────────────────

@router.message(Command("admin"))
async def admin_panel(message: Message):
    await message.answer(
        "⚙️ <b>Панель администратора</b>\n\n"
        "/all_bookings — все заявки\n"
        "/stats        — статистика",
        parse_mode="HTML"
    )


# ─── ВСЕ ЗАЯВКИ ───────────────────────────────────────────

def _booking_text(b: dict) -> str:
    """Форматирует текст одной заявки для вывода в чат."""
    status_label = BOOKING_STATUSES.get(b["status"], b["status"])
    vin_line    = f"\n🔑 VIN: {b['vin']}" if b.get("vin") else ""
    comment_line = f"\n\n💬 <b>Комментарий:</b> <i>{b['comment']}</i>" if b.get("comment") else ""
    return (
        f"<b>Заявка №{b['id']}</b>  |  {status_label}\n"
        f"🔧 {b['service']}\n"
        f"👤 {b['name']}  📞 {b['phone']}\n"
        f"🚗 {b.get('car_brand','')} {b.get('car_model','')} ({b.get('car_year','')})"
        f"{vin_line}\n"
        f"📅 {b.get('visit_date','')}  🕐 {b.get('visit_time','')}\n"
        f"🆔 @{b.get('username') or '—'}  (ID: {b['user_id']})\n"
        f"🗓 Создана: {b['created_at'][:16]}"
        f"{comment_line}"
    )


@router.message(Command("all_bookings"))
async def all_bookings(message: Message):
    bookings = await get_all_bookings()
    if not bookings:
        await message.answer("📭 Заявок пока нет.")
        return

    await message.answer(f"📋 <b>Всего заявок: {len(bookings)}</b>", parse_mode="HTML")
    for b in bookings:
        await message.answer(
            _booking_text(b),
            parse_mode="HTML",
            reply_markup=admin_booking_keyboard(b["id"])
        )


# ─── СМЕНА СТАТУСА ЗАЯВКИ ─────────────────────────────────

# Уведомления клиенту при смене статуса
STATUS_NOTIFICATIONS = {
    "confirmed": "✅ Ваша заявка подтверждена! Ждём вас.",
    "in_work":   "🔨 Ваш автомобиль принят в работу.",
    "done":      "🏁 Работы завершены! Ваш автомобиль готов. Спасибо, что выбрали нас!",
    "pending":   "⏳ Статус вашей заявки изменён на «Ожидает подтверждения».",
}


@router.callback_query(F.data.startswith("set_status:"))
async def set_status(callback: CallbackQuery):
    """
    callback.data = "set_status:confirmed:42"
    Разбираем по ':' → [set_status, confirmed, 42]
    """
    _, new_status, booking_id_str = callback.data.split(":")
    booking_id = int(booking_id_str)

    await update_booking_status(booking_id, new_status)
    await callback.answer(f"Статус: {BOOKING_STATUSES.get(new_status, new_status)}")

    booking = await get_booking_by_id(booking_id)
    if booking:
        await callback.message.edit_text(
            _booking_text(booking),
            parse_mode="HTML",
            reply_markup=admin_booking_keyboard(booking_id)
        )
        # Уведомляем клиента
        notification = STATUS_NOTIFICATIONS.get(new_status)
        if notification:
            comment_part = f"\n\n💬 <i>{booking['comment']}</i>" if booking.get("comment") else ""
            try:
                await callback.bot.send_message(
                    booking["user_id"],
                    f"🔔 <b>Обновление по заявке №{booking_id}</b>\n\n"
                    f"{notification}{comment_part}",
                    parse_mode="HTML"
                )
            except Exception:
                pass


# ─── ДОБАВИТЬ КОММЕНТАРИЙ К ЗАЯВКЕ ────────────────────────

@router.callback_query(F.data.startswith("add_comment:"))
async def add_comment_start(callback: CallbackQuery, state: FSMContext):
    """Запускаем FSM — ждём текст комментария."""
    booking_id = int(callback.data.split(":")[1])
    await state.set_state(AdminStates.waiting_comment)
    await state.update_data(booking_id=booking_id)
    await callback.answer()
    await callback.message.answer(
        f"💬 Введите комментарий к заявке №{booking_id}:\n"
        f"<i>Он будет виден клиенту в «Мои записи» и в уведомлениях.</i>",
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_comment, F.text)
async def save_comment(message: Message, state: FSMContext):
    """Сохраняем комментарий и обновляем сообщение с заявкой."""
    data = await state.get_data()
    booking_id = data["booking_id"]
    comment = message.text.strip()

    await update_booking_comment(booking_id, comment)
    await state.clear()

    booking = await get_booking_by_id(booking_id)
    await message.answer(
        f"✅ Комментарий к заявке №{booking_id} сохранён:\n<i>{comment}</i>",
        parse_mode="HTML"
    )
    # Уведомляем клиента о новом комментарии
    if booking:
        try:
            await message.bot.send_message(
                booking["user_id"],
                f"💬 <b>Комментарий по заявке №{booking_id}:</b>\n\n<i>{comment}</i>",
                parse_mode="HTML"
            )
        except Exception:
            pass


# ─── ОТВЕТ НА ВОПРОС МАСТЕРУ ──────────────────────────────

@router.callback_query(F.data.startswith("answer_question:"))
async def answer_question_start(callback: CallbackQuery, state: FSMContext):
    """Запускаем FSM — ждём текст ответа."""
    question_id = int(callback.data.split(":")[1])
    question = await get_question_by_id(question_id)

    await state.set_state(AdminStates.waiting_answer)
    await state.update_data(
        question_id=question_id,
        client_user_id=question["user_id"] if question else None
    )
    await callback.answer()

    preview = ""
    if question and question.get("question_text"):
        preview = f"\n\n<b>Вопрос:</b> <i>{question['question_text']}</i>"

    await callback.message.answer(
        f"✍️ Введите ответ на вопрос №{question_id}:{preview}\n\n"
        f"<i>Ответ будет отправлен клиенту в Telegram.</i>",
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_answer, F.text)
async def send_answer(message: Message, state: FSMContext):
    """Отправляем ответ клиенту и сохраняем в БД."""
    data = await state.get_data()
    question_id  = data["question_id"]
    client_user_id = data["client_user_id"]
    answer_text  = message.text.strip()

    await save_answer(question_id, answer_text)
    await state.clear()

    # Отправляем ответ клиенту
    if client_user_id:
        try:
            await message.bot.send_message(
                client_user_id,
                f"💬 <b>Ответ мастера:</b>\n\n{answer_text}",
                parse_mode="HTML"
            )
            await message.answer(f"✅ Ответ на вопрос №{question_id} отправлен клиенту.")
        except Exception:
            await message.answer(
                f"⚠️ Не удалось доставить ответ клиенту (возможно, заблокировал бота).\n"
                f"Ответ сохранён в базе данных."
            )
    else:
        await message.answer("⚠️ Не удалось найти клиента для ответа.")


# ─── СТАТИСТИКА ───────────────────────────────────────────

@router.message(Command("stats"))
async def stats(message: Message):
    bookings = await get_all_bookings()
    total = len(bookings)
    counts = {k: 0 for k in BOOKING_STATUSES}
    for b in bookings:
        if b["status"] in counts:
            counts[b["status"]] += 1

    lines = "\n".join(
        f"{label}: {counts[key]}"
        for key, label in BOOKING_STATUSES.items()
    )
    await message.answer(
        f"📊 <b>Статистика заявок</b>\n\n"
        f"Всего: <b>{total}</b>\n\n"
        f"{lines}",
        parse_mode="HTML"
    )
