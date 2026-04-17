"""
handlers/info.py — прайс, контакты, вопрос мастеру.

Вопрос мастеру теперь принимает:
  — текстовые сообщения
  — фото (photo)
  — видео (video)
  — голосовые сообщения (voice)
  — документы (document)
  — видеокружки (video_note)

Каждый вопрос сохраняется в БД и пересылается администратору
с кнопкой «Ответить». Администратор пишет ответ — он
доставляется клиенту от имени бота.
"""

import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from config import PRICE_PDF_PATH, ADMIN_ID
from keyboards import main_menu, cancel_keyboard, admin_answer_keyboard
from states import QuestionStates
from database.db import add_question

router = Router()


# ─── ПРАЙС-ЛИСТ ───────────────────────────────────────────

@router.message(F.text == "💰 Узнать стоимость")
async def send_price(message: Message):
    from aiogram.types import FSInputFile
    if not os.path.exists(PRICE_PDF_PATH):
        await message.answer(
            "⚠️ Прайс-лист временно недоступен. Позвоните нам: +7 (995) 794-21-29",
            reply_markup=main_menu()
        )
        return
    await message.answer_document(
        FSInputFile(PRICE_PDF_PATH, filename="Прайс_Починим_и_точка.pdf"),
        caption="💰 <b>Прайс-лист автосервиса «Починим и точка»</b>",
        parse_mode="HTML"
    )


# ─── АКЦИИ ────────────────────────────────────────────────

@router.message(F.text == "🎁 Акции")
async def send_promos(message: Message):
    await message.answer(
        "🎁 <b>Акции автосервиса «Починим и точка»</b>\n\n"
        "Актуальных акций на данный момент нет.",
        parse_mode="HTML",
        reply_markup=main_menu()
    )




@router.message(F.text == "📞 Контакты")
async def send_contacts(message: Message):
    await message.answer(
        "📞 <b>Контакты автосервиса «Починим и точка»</b>\n\n"
        "📍 Адрес: Рассветная аллея, 5А\n"
        "📱 Телефон: +7 (995) 794-21-29\n"
        "🕐 Режим работы: ежедневно 10:00–21:00",
        parse_mode="HTML",
        reply_markup=main_menu()
    )


# ─── ВОПРОС МАСТЕРУ: СТАРТ ────────────────────────────────

@router.message(F.text == "❓ Вопрос мастеру")
async def ask_question_start(message: Message, state: FSMContext):
    await state.set_state(QuestionStates.waiting_question)
    await message.answer(
        "✍️ <b>Отправьте ваш вопрос мастеру:</b>\n\n"
        "Можно написать текст, прикрепить фото, видео,\n"
        "голосовое сообщение или документ.",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )


# ─── ВОПРОС: ТЕКСТ ────────────────────────────────────────

@router.message(QuestionStates.waiting_question, F.text)
async def receive_text_question(message: Message, state: FSMContext):
    await _save_and_forward_question(
        message=message,
        state=state,
        question_text=message.text,
        media_type=None,
        media_file_id=None,
    )


# ─── ВОПРОС: ФОТО ─────────────────────────────────────────

@router.message(QuestionStates.waiting_question, F.photo)
async def receive_photo_question(message: Message, state: FSMContext):
    # Telegram присылает несколько размеров фото — берём самый большой ([-1])
    file_id = message.photo[-1].file_id
    await _save_and_forward_question(
        message=message,
        state=state,
        question_text=message.caption,
        media_type="photo",
        media_file_id=file_id,
    )


# ─── ВОПРОС: ВИДЕО ────────────────────────────────────────

@router.message(QuestionStates.waiting_question, F.video)
async def receive_video_question(message: Message, state: FSMContext):
    await _save_and_forward_question(
        message=message,
        state=state,
        question_text=message.caption,
        media_type="video",
        media_file_id=message.video.file_id,
    )


# ─── ВОПРОС: ГОЛОСОВОЕ ────────────────────────────────────

@router.message(QuestionStates.waiting_question, F.voice)
async def receive_voice_question(message: Message, state: FSMContext):
    await _save_and_forward_question(
        message=message,
        state=state,
        question_text=None,
        media_type="voice",
        media_file_id=message.voice.file_id,
    )


# ─── ВОПРОС: ДОКУМЕНТ ─────────────────────────────────────

@router.message(QuestionStates.waiting_question, F.document)
async def receive_document_question(message: Message, state: FSMContext):
    await _save_and_forward_question(
        message=message,
        state=state,
        question_text=message.caption,
        media_type="document",
        media_file_id=message.document.file_id,
    )


# ─── ВОПРОС: ВИДЕОКРУЖОК ──────────────────────────────────

@router.message(QuestionStates.waiting_question, F.video_note)
async def receive_video_note_question(message: Message, state: FSMContext):
    await _save_and_forward_question(
        message=message,
        state=state,
        question_text=None,
        media_type="video_note",
        media_file_id=message.video_note.file_id,
    )


# ─── ОТМЕНА ВОПРОСА ───────────────────────────────────────

@router.callback_query(QuestionStates.waiting_question, F.data == "cancel_booking")
async def cancel_question(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Отменено")
    await callback.message.edit_text("❌ Отменено.")
    await callback.message.answer("Главное меню:", reply_markup=main_menu())


# ─── ВНУТРЕННЯЯ ФУНКЦИЯ: сохранить и переслать ────────────

async def _save_and_forward_question(
    message: Message,
    state: FSMContext,
    question_text: str | None,
    media_type: str | None,
    media_file_id: str | None,
):
    """
    Общая логика для всех типов медиа:
    1. Сохраняем вопрос в БД
    2. Сбрасываем состояние
    3. Отправляем сообщение + медиа администратору
    4. Добавляем кнопку "Ответить"
    5. Подтверждаем клиенту
    """
    user = message.from_user
    display_name = user.full_name or user.username or str(user.id)

    question_id = await add_question(
        user_id=user.id,
        username=user.username or "",
        user_name=display_name,
        question_text=question_text,
        media_type=media_type,
        media_file_id=media_file_id,
    )

    await state.clear()

    # Шапка уведомления для администратора
    header = (
        f"❓ <b>Вопрос №{question_id} мастеру</b>\n\n"
        f"От: <b>{display_name}</b>  @{user.username or '—'}  (ID: {user.id})\n"
    )
    if question_text:
        header += f"\n<b>Текст:</b> {question_text}\n"

    reply_markup = admin_answer_keyboard(question_id)

    try:
        if media_type == "photo":
            await message.bot.send_photo(
                ADMIN_ID, photo=media_file_id,
                caption=header, parse_mode="HTML",
                reply_markup=reply_markup
            )
        elif media_type == "video":
            await message.bot.send_video(
                ADMIN_ID, video=media_file_id,
                caption=header, parse_mode="HTML",
                reply_markup=reply_markup
            )
        elif media_type == "voice":
            # Для голосового сначала текст-шапку, потом голосовое
            await message.bot.send_message(ADMIN_ID, header, parse_mode="HTML")
            await message.bot.send_voice(
                ADMIN_ID, voice=media_file_id,
                reply_markup=reply_markup
            )
        elif media_type == "document":
            await message.bot.send_document(
                ADMIN_ID, document=media_file_id,
                caption=header, parse_mode="HTML",
                reply_markup=reply_markup
            )
        elif media_type == "video_note":
            await message.bot.send_message(ADMIN_ID, header, parse_mode="HTML")
            await message.bot.send_video_note(
                ADMIN_ID, video_note=media_file_id,
                reply_markup=reply_markup
            )
        else:
            # Только текст
            await message.bot.send_message(
                ADMIN_ID, header,
                parse_mode="HTML",
                reply_markup=reply_markup
            )

        await message.answer(
            f"✅ Вопрос отправлен мастеру!\n"
            f"Ожидайте ответа в этом чате.",
            reply_markup=main_menu()
        )

    except Exception as e:
        await message.answer(
            "⚠️ Не удалось отправить вопрос. Позвоните нам: +7 (995) 794-21-29",
            reply_markup=main_menu()
        )
