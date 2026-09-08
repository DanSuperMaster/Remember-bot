import asyncio
from datetime import datetime, timedelta

from aiogram import Bot

from config import MOSCOW_TZ
from db import (
    cleanup_old_reminders,
    get_due_reminders,
    update_reminder_after_send,
)
from keyboards import build_reminder_keyboard


async def check_reminders(bot: Bot):
    last_cleanup_time = datetime.min.replace(tzinfo=MOSCOW_TZ)
    CLEANUP_INTERVAL = timedelta(hours=24)

    while True:
        try:
            now_moscow = datetime.now(MOSCOW_TZ)

            if now_moscow - last_cleanup_time >= CLEANUP_INTERVAL:
                deleted_count = await cleanup_old_reminders(now_moscow)
                print(
                    f"Очистка БД: удалены устаревшие/неактивные записи ({deleted_count})"
                )
                last_cleanup_time = now_moscow

            reminders = await get_due_reminders(now_moscow)

            if not reminders:
                await asyncio.sleep(10)
                continue

            for r in reminders:
                reminder_id = r["id"]
                user_id = r["user_id"]
                message_text = r["message"]
                repeat_interval = r["repeat_interval"]

                keyboard = build_reminder_keyboard(
                    reminder_id, is_repeatable=bool(repeat_interval)
                )

                sent_successfully = False
                try:
                    await bot.send_message(
                        chat_id=user_id,
                        text=f"🔔 **Напоминание:**\n\n{message_text}",
                        reply_markup=keyboard,
                        parse_mode="Markdown",
                    )
                    sent_successfully = True
                except Exception as send_error:
                    print(f"❌ Ошибка отправки пользователю {user_id}: {send_error}")

                if sent_successfully:
                    await update_reminder_after_send(
                        reminder_id, repeat_interval, now_moscow
                    )

        except Exception as e:
            print(f"❌ Критическая ошибка в фоновом цикле: {e}")

        await asyncio.sleep(10)
