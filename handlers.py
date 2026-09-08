import re
from datetime import datetime, timedelta

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback

import db
from config import MOSCOW_TZ
from keyboards import DAY_TIMES, REPETITION_TIMES, TIME_TIMES
from states import User

router = Router()


@router.message(Command("start"))
async def start_message(message: types.Message):
    await message.answer("Это бот, который создан для того, чтобы напоминать о чём-то.")


@router.message(Command("start_notification"))
async def get_notification(message: types.Message, state: FSMContext):
    await state.clear()
    builder = InlineKeyboardBuilder()

    await state.set_state(User.waiting_for_day)
    await state.update_data(user_id=message.from_user.id)

    for i in range(len(DAY_TIMES)):
        builder.add(
            types.InlineKeyboardButton(text=DAY_TIMES[i], callback_data=f"select_{i}")
        )

    builder.adjust(2)
    await message.answer(
        "Выберите дату из списка ниже:", reply_markup=builder.as_markup()
    )


@router.callback_query(F.data.startswith("select_"), User.waiting_for_day)
async def process_selection_time(callback: types.CallbackQuery, state: FSMContext):
    date_id = int(callback.data.split("_")[1])
    selected_option = DAY_TIMES[date_id]

    if selected_option == "Кастомное":
        await callback.answer()
        calendar = SimpleCalendar()
        now = datetime.now(MOSCOW_TZ)
        calendar_markup = await calendar.start_calendar(year=now.year, month=now.month)
        await callback.message.edit_text(
            "Выберите дату на календаре:", reply_markup=calendar_markup
        )
        return

    now_date = datetime.now(MOSCOW_TZ).date()
    if selected_option == "Сегодня":
        target_date = now_date
    elif selected_option == "Завтра":
        target_date = now_date + timedelta(days=1)
    elif selected_option == "Через неделю":
        target_date = now_date + timedelta(weeks=1)

    await state.update_data(
        day=selected_option, day_iso=target_date.strftime("%Y-%m-%d")
    )
    await state.set_state(User.waiting_for_time)

    builder = InlineKeyboardBuilder()
    for i in range(len(TIME_TIMES)):
        builder.add(
            types.InlineKeyboardButton(text=TIME_TIMES[i], callback_data=f"time_{i}")
        )
    builder.adjust(2)

    await callback.answer(f"Вы выбрали: {selected_option}")
    await callback.message.edit_text(
        f"Вы выбрали день: {selected_option}\nТеперь выберите время:",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(SimpleCalendarCallback.filter(), User.waiting_for_day)
async def process_custom_date(
    callback: types.CallbackQuery,
    callback_data: SimpleCalendarCallback,
    state: FSMContext,
):
    calendar = SimpleCalendar()
    selected, date = await calendar.process_selection(callback, callback_data)

    if selected:
        formatted_date = date.strftime("%d.%m.%Y")
        await state.update_data(day=formatted_date, day_iso=date.strftime("%Y-%m-%d"))
        await state.set_state(User.waiting_for_time)

        builder = InlineKeyboardBuilder()
        for i in range(len(TIME_TIMES)):
            builder.add(
                types.InlineKeyboardButton(
                    text=TIME_TIMES[i], callback_data=f"time_{i}"
                )
            )
        builder.adjust(2)

        await callback.message.edit_text(
            f"Вы выбрали дату: {formatted_date}\nТеперь выберите время:",
            reply_markup=builder.as_markup(),
        )


@router.callback_query(F.data.startswith("time_"), User.waiting_for_time)
async def process_selection_repetition(
    callback: types.CallbackQuery, state: FSMContext
):
    time_id = int(callback.data.split("_")[1])
    selected_option = TIME_TIMES[time_id]

    if selected_option == "Кастомное":
        await callback.answer()
        await state.set_state(User.waiting_for_custom_time)
        await callback.message.edit_text(
            "Введите время в формате **ЧЧ:ММ** (например, 14:30 или 09:00):",
            parse_mode="Markdown",
        )
        return

    time_clean = selected_option.replace("в ", "").strip()
    await state.update_data(time=selected_option, time_val=time_clean)
    await state.set_state(User.waiting_for_repeat)

    builder = InlineKeyboardBuilder()
    for i in range(len(REPETITION_TIMES)):
        builder.add(
            types.InlineKeyboardButton(
                text=REPETITION_TIMES[i], callback_data=f"repetition_{i}"
            )
        )
    builder.adjust(2)

    await callback.answer(f"Вы выбрали: {selected_option}")
    await callback.message.edit_text(
        f"Вы выбрали время: {selected_option}\nТеперь выберите повторение:",
        reply_markup=builder.as_markup(),
    )


@router.message(User.waiting_for_custom_time)
async def process_custom_time_input(message: types.Message, state: FSMContext):
    time_text = message.text.strip().replace(".", ":")

    if not re.match(r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$", time_text):
        await message.answer(
            "Некорректный формат времени! Пожалуйста, введите время в формате **ЧЧ:ММ** (например, 15:45):",
            parse_mode="Markdown",
        )
        return

    h, m = time_text.split(":")
    formatted_time = f"{int(h):02d}:{int(m):02d}"

    await state.update_data(time=f"в {formatted_time}", time_val=formatted_time)
    await state.set_state(User.waiting_for_repeat)

    builder = InlineKeyboardBuilder()
    for i in range(len(REPETITION_TIMES)):
        builder.add(
            types.InlineKeyboardButton(
                text=REPETITION_TIMES[i], callback_data=f"repetition_{i}"
            )
        )
    builder.adjust(2)

    await message.answer(
        f"Вы выбрали время: в {formatted_time}\nТеперь выберите повторение:",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data.startswith("repetition_"), User.waiting_for_repeat)
async def process_selection_text(callback: types.CallbackQuery, state: FSMContext):
    repetition_id = int(callback.data.split("_")[1])
    selected_option = REPETITION_TIMES[repetition_id]

    if selected_option == "Кастомное":
        await callback.answer()
        await state.set_state(User.waiting_for_custom_repeat)
        await callback.message.edit_text(
            "Введите интервал повторения в формате **ДД:ЧЧ:ММ**\n"
            "(где ДД — дни, ЧЧ — часы, ММ — минуты, например: `01:12:30`):",
            parse_mode="Markdown",
        )
        return

    interval_map = {
        "Нет повторения": None,
        "Каждый день": timedelta(days=1),
        "Каждую неделю": timedelta(weeks=1),
        "Каждый месяц": timedelta(days=30),
    }

    await state.update_data(
        repetion=selected_option,
        repeat_interval=interval_map.get(selected_option),
    )
    await state.set_state(User.waiting_for_text)

    await callback.answer(f"Вы выбрали: {selected_option}")
    await callback.message.edit_text(
        f"Вы выбрали повторение: {selected_option}\nТеперь введите текст напоминания сообщением:"
    )


@router.message(User.waiting_for_custom_repeat)
async def process_custom_repeat_input(message: types.Message, state: FSMContext):
    repeat_text = message.text.strip().replace(".", ":")

    if not re.match(r"^\d{2}:([01]\d|2[0-3]):[0-5]\d$", repeat_text):
        await message.answer(
            "Некорректный формат! Введите интервал в формате **ДД:ЧЧ:ММ** (например, `00:08:00`):",
            parse_mode="Markdown",
        )
        return

    days, hours, minutes = map(int, repeat_text.split(":"))

    pg_interval = timedelta(days=days, hours=hours, minutes=minutes)
    selected_repeat = f"Каждые {days}д. {hours}ч. {minutes}мин."

    await state.update_data(repetion=selected_repeat, repeat_interval=pg_interval)
    await state.set_state(User.waiting_for_text)

    await message.answer(
        f"Вы выбрали повторение: {selected_repeat}\nТеперь введите текст напоминания сообщением:"
    )


@router.message(User.waiting_for_text)
async def process_text_input(message: types.Message, state: FSMContext):
    text = message.text.strip()
    await state.update_data(text=text)
    await state.set_state(User.waiting_for_confirmation)

    user_data = await state.get_data()

    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(text="Подтвердить", callback_data="confirm_yes")
    )
    builder.add(types.InlineKeyboardButton(text="Отмена", callback_data="confirm_no"))
    builder.adjust(2)

    summary = (
        "**Проверьте данные вашего напоминания:**\n\n"
        f"**Дата:** {user_data.get('day')}\n"
        f"**Время:** {user_data.get('time')}\n"
        f"**Повторение:** {user_data.get('repetion')}\n"
        f"**Текст:** {user_data.get('text')}\n\n"
        "Всё верно?"
    )

    await message.answer(
        summary, reply_markup=builder.as_markup(), parse_mode="Markdown"
    )


@router.callback_query(F.data == "confirm_yes", User.waiting_for_confirmation)
async def process_confirm(callback: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()

    day_iso = user_data.get("day_iso")
    time_val = user_data.get("time_val")

    now_moscow = datetime.now(MOSCOW_TZ)

    if not day_iso:
        day_str = user_data.get("day", "")
        if "сегодня" in day_str.lower():
            day_iso = now_moscow.strftime("%Y-%m-%d")
        elif "завтра" in day_str.lower():
            day_iso = (now_moscow + timedelta(days=1)).strftime("%Y-%m-%d")
        elif "неделю" in day_str.lower():
            day_iso = (now_moscow + timedelta(weeks=1)).strftime("%Y-%m-%d")
        else:
            try:
                parsed_date = datetime.strptime(day_str, "%d.%m.%Y")
                day_iso = parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                day_iso = now_moscow.strftime("%Y-%m-%d")

    if not time_val:
        time_str = user_data.get("time", "10:00").replace("в ", "").strip()
        time_val = time_str

    dt_string = f"{day_iso} {time_val}"

    naive_dt = datetime.strptime(dt_string, "%Y-%m-%d %H:%M")
    target_datetime = naive_dt.replace(tzinfo=MOSCOW_TZ)

    user_id = user_data["user_id"]
    repeat_interval = user_data.get("repeat_interval")
    message_text = user_data["text"]

    try:
        await db.create_reminder(
            user_id, target_datetime, repeat_interval, message_text
        )
        await callback.answer("Сохранено!")
        await callback.message.edit_text(
            "🎉 **Напоминание успешно создано и сохранено в Базу Данных!**",
            parse_mode="Markdown",
        )
    except Exception as e:
        print(f"Ошибка при записи в БД: {e}")
        await callback.answer("Ошибка при сохранении!")
        await callback.message.edit_text(
            "❌ Произошла ошибка при сохранении в базу данных."
        )

    await state.clear()


@router.callback_query(F.data == "confirm_no", User.waiting_for_confirmation)
async def process_cancel(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Отменено")
    await callback.message.edit_text("❌ Создание напоминания отменено.")
    await state.clear()


@router.callback_query(F.data.startswith("rem_delay_"))
async def process_reminder_delay(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    minutes = int(parts[2])
    reminder_id = int(parts[3])

    new_time = datetime.now(MOSCOW_TZ) + timedelta(minutes=minutes)

    try:
        await db.delay_reminder(reminder_id, new_time)
        await callback.answer(f"Отложено на {minutes} мин.")
        await callback.message.edit_text(
            f"{callback.message.text}\n\n⏳ *Отложено на {minutes} минут*",
            parse_mode="Markdown",
        )
    except Exception as e:
        print(f"Ошибка при переносе напоминания: {e}")
        await callback.answer("Ошибка при изменении времени.")


@router.callback_query(F.data.startswith("rem_done_"))
async def process_reminder_done(callback: types.CallbackQuery):
    reminder_id = int(callback.data.split("_")[2])

    try:
        await db.deactivate_reminder(reminder_id)
        await callback.answer("Выполнено!")
        await callback.message.edit_text(
            f"{callback.message.text}\n\n✅ *Выполнено*", parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Ошибка при отметке выполнения: {e}")
        await callback.answer("Ошибка!")


@router.callback_query(F.data.startswith("rem_stop_"))
async def process_reminder_stop(callback: types.CallbackQuery):
    reminder_id = int(callback.data.split("_")[2])

    try:
        await db.deactivate_reminder(reminder_id)
        await callback.answer("Повторение остановлено!")
        await callback.message.edit_text(
            f"{callback.message.text}\n\n🛑 *Повторение завершено*",
            parse_mode="Markdown",
        )
    except Exception as e:
        print(f"Ошибка при остановке повторений: {e}")
        await callback.answer("Ошибка!")
