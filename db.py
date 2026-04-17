"""
database/db.py — работа с базой данных SQLite.

Таблицы:
  bookings  — заявки клиентов
  questions — вопросы мастеру (с возможностью ответа)

Новые поля в bookings:
  car_brand   — марка автомобиля (Toyota, BMW...)
  car_model   — модель (Camry, X5...)
  car_year    — год выпуска (2018)
  vin         — VIN-код (необязательный)
  visit_date  — желаемая дата посещения
  visit_time  — желаемое время посещения
  comment     — комментарий администратора к заявке

Статусы заявки:
  pending     — ожидает подтверждения
  confirmed   — подтверждено
  in_work     — в работе
  done        — завершено
"""

import aiosqlite

DB_PATH = "database/autoservice.db"


async def init_db():
    """Создаёт все таблицы при первом запуске."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                username    TEXT,
                service     TEXT NOT NULL,
                name        TEXT NOT NULL,
                phone       TEXT NOT NULL,
                car_brand   TEXT,
                car_model   TEXT,
                car_year    TEXT,
                vin         TEXT,
                visit_date  TEXT,
                visit_time  TEXT,
                status      TEXT DEFAULT 'pending',
                comment     TEXT,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL,
                username      TEXT,
                user_name     TEXT,
                question_text TEXT,
                media_type    TEXT,
                media_file_id TEXT,
                answer_text   TEXT,
                answered_at   DATETIME,
                created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


async def add_booking(
    user_id: int, username: str, service: str,
    name: str, phone: str,
    car_brand: str, car_model: str, car_year: str,
    vin: str, visit_date: str, visit_time: str
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO bookings
               (user_id, username, service, name, phone,
                car_brand, car_model, car_year, vin, visit_date, visit_time)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, username, service, name, phone,
             car_brand, car_model, car_year, vin, visit_date, visit_time)
        )
        await db.commit()
        return cursor.lastrowid


async def get_user_bookings(user_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM bookings WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_all_bookings() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM bookings ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_booking_by_id(booking_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_booking_status(booking_id: int, new_status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE bookings SET status = ? WHERE id = ?", (new_status, booking_id))
        await db.commit()


async def update_booking_comment(booking_id: int, comment: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE bookings SET comment = ? WHERE id = ?", (comment, booking_id))
        await db.commit()


async def add_question(
    user_id: int, username: str, user_name: str,
    question_text: str = None,
    media_type: str = None,
    media_file_id: str = None
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO questions
               (user_id, username, user_name, question_text, media_type, media_file_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, username, user_name, question_text, media_type, media_file_id)
        )
        await db.commit()
        return cursor.lastrowid


async def get_question_by_id(question_id: int) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM questions WHERE id = ?", (question_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def save_answer(question_id: int, answer_text: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE questions SET answer_text = ?, answered_at = CURRENT_TIMESTAMP WHERE id = ?",
            (answer_text, question_id)
        )
        await db.commit()
