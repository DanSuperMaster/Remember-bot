from datetime import datetime, timedelta

import asyncpg

from config import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER

db_pool: asyncpg.Pool = None


async def init_db():
    global db_pool
    db_pool = await asyncpg.create_pool(
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        host=DB_HOST,
        port=DB_PORT,
        ssl=False,
    )

    async with db_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                target_datetime TIMESTAMPTZ NOT NULL,
                repeat_interval INTERVAL DEFAULT NULL,
                message TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
        """)


async def cleanup_old_reminders(now_moscow: datetime) -> str:
    async with db_pool.acquire() as conn:
        return await conn.execute(
            """
            DELETE FROM reminders
            WHERE is_active = FALSE OR (repeat_interval IS NULL AND target_datetime < $1);
            """,
            now_moscow - timedelta(hours=3),
        )


async def get_due_reminders(now_moscow: datetime):
    async with db_pool.acquire() as conn:
        return await conn.fetch(
            """
            SELECT id, user_id, message, repeat_interval
            FROM reminders
            WHERE is_active = TRUE AND target_datetime <= $1;
            """,
            now_moscow,
        )


async def update_reminder_after_send(
    reminder_id: int, repeat_interval, now_moscow: datetime
):
    async with db_pool.acquire() as conn:
        if repeat_interval:
            await conn.execute(
                """
                UPDATE reminders
                SET target_datetime = target_datetime + $1
                WHERE id = $2;
                """,
                repeat_interval,
                reminder_id,
            )
        else:
            temp_future_time = now_moscow + timedelta(hours=3)
            await conn.execute(
                """
                UPDATE reminders
                SET target_datetime = $1
                WHERE id = $2;
                """,
                temp_future_time,
                reminder_id,
            )


async def delay_reminder(reminder_id: int, new_time: datetime):
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE reminders
            SET target_datetime = $1, is_active = TRUE
            WHERE id = $2;
            """,
            new_time,
            reminder_id,
        )


async def deactivate_reminder(reminder_id: int):
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE reminders
            SET is_active = FALSE
            WHERE id = $1;
            """,
            reminder_id,
        )


async def create_reminder(
    user_id: int, target_datetime: datetime, repeat_interval, message_text: str
):
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO reminders (user_id, target_datetime, repeat_interval, message)
            VALUES ($1, $2, $3, $4);
            """,
            user_id,
            target_datetime,
            repeat_interval,
            message_text,
        )
