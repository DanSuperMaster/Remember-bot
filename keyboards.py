from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

DAY_TIMES = ["Сегодня", "Завтра", "Через неделю", "Кастомное"]
TIME_TIMES = ["в 10:00", "в 14:00", "в 18:00", "Кастомное"]
REPETITION_TIMES = [
    "Нет повторения",
    "Каждый день",
    "Каждую неделю",
    "Каждый месяц",
    "Кастомное",
]


def build_reminder_keyboard(
    reminder_id: int, is_repeatable: bool
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text="+15 мин", callback_data=f"rem_delay_15_{reminder_id}"
        )
    )
    builder.add(
        InlineKeyboardButton(
            text="+30 мин", callback_data=f"rem_delay_30_{reminder_id}"
        )
    )
    builder.add(
        InlineKeyboardButton(text="+1 час", callback_data=f"rem_delay_60_{reminder_id}")
    )

    if is_repeatable:
        builder.add(
            InlineKeyboardButton(
                text="❌ Завершить (отключить)",
                callback_data=f"rem_stop_{reminder_id}",
            )
        )
    else:
        builder.add(
            InlineKeyboardButton(
                text="✅ Выполнено", callback_data=f"rem_done_{reminder_id}"
            )
        )

    builder.adjust(3, 1)
    return builder.as_markup()
