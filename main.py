"""
main.py — точка входа в бот.

Здесь мы:
1. Создаём объект Bot с нашим токеном
2. Создаём Dispatcher (он управляет обновлениями)
3. Подключаем роутеры (handlers)
4. Запускаем polling (бот слушает новые сообщения)
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import TOKEN
from database.db import init_db
from handlers import start, booking, admin, info


async def main():
    # Настраиваем логирование — будем видеть ошибки в консоли
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    # Инициализируем базу данных (создаём таблицы если их нет)
    await init_db()

    # Создаём бота
    bot = Bot(token=TOKEN)

    # MemoryStorage хранит состояния FSM в памяти (подходит для небольших ботов)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Подключаем роутеры в правильном порядке
    # (порядок важен: более специфичные — первыми)
    dp.include_router(admin.router)    # Админ-команды
    dp.include_router(booking.router)  # FSM запись клиента
    dp.include_router(info.router)     # Прайс, контакты, вопрос мастеру
    dp.include_router(start.router)    # Старт и главное меню (последним — самый общий)

    print("✅ Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
