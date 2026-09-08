import asyncio
import os
import re
from datetime import datetime, timedelta

import asyncpg
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback
from dotenv import load_dotenv

load_dotenv("ApiKeyFile.env")
bot = Bot(token=os.getenv("API_KEY"))
dp = Dispatcher(storage=MemoryStorage())

DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")
DB_HOST = "localhost"
DB_PORT = 16500

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
                target_datetime TIMESTAMP NOT NULL,
                repeat_interval INTERVAL DEFAULT NULL,
                message TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)


class User(StatesGroup):
    waiting_for_day = State()
    waiting_for_time = State()
    waiting_for_custom_time = State()
    waiting_for_repeat = State()
    waiting_for_custom_repeat = State()
    waiting_for_text = State()
    waiting_for_confirmation = State()


dayTimes = ["Сегодня", "Завтра", "Через неделю", "Кастомное"]
timeTimes = ["в 10:00", "в 14:00", "в 18:00", "Кастомное"]
repetionTimes = [
    "Нет повторения",
    "Каждый день",
    "Каждую неделю",
    "Каждый месяц",
    "Кастомное",
]


async def check_reminders(bot: Bot, pool: asyncpg.Pool):
    while True:
        try:
            async with pool.acquire() as conn:
                reminders = await conn.fetch("""
                    SELECT id, user_id, message, repeat_interval
                    FROM reminders
                    WHERE is_active = TRUE AND target_datetime <= NOW();
                """)

                # Если ничего нет — идем на следующий круг
                if not reminders:
                    await asyncio.sleep(10)
                    continue
                else:
                    print("Need to remaind: " + len(reminders))

                for r in reminders:
                    reminder_id = r["id"]
                    user_id = r["user_id"]
                    message_text = r["message"]
                    repeat_interval = r["repeat_interval"]

                    # 2. Пытаемся отправить сообщение
                    sent_successfully = False
                    try:
                        await bot.send_message(
                            chat_id=user_id,
                            text=f"🔔 **Напоминание:**\n\n{message_text}",
                            parse_mode="Markdown",
                        )
                        sent_successfully = True
                    except Exception as send_error:
                        print(
                            f"❌ Ошибка отправки пользователю {user_id}: {send_error}"
                        )

                    # 3. Обновляем БД только если сообщение успешно ушло (или если нужно деактивировать битые)
                    if sent_successfully:
                        if repeat_interval:
                            await conn.execute(
                                """
                                UPDATE reminders
                                SET target_datetime = target_datetime + repeat_interval
                                WHERE id = $1;
                            """,
                                reminder_id,
                            )
                        else:
                            await conn.execute(
                                """
                                UPDATE reminders
                                SET is_active = FALSE
                                WHERE id = $1;
                            """,
                                reminder_id,
                            )

        except Exception as e:
            print(f"❌ Критическая ошибка в фоновом цикле: {e}")

        await asyncio.sleep(10)


@dp.message(Command("start"))
async def start_message(message: types.Message):
    await message.answer("Это бот, который создан для того, чтобы напоминать о чём-то.")


@dp.message(Command("start_notification"))
async def getNotification(message: types.Message, state: FSMContext):
    await state.clear()
    builder = InlineKeyboardBuilder()

    await state.set_state(User.waiting_for_day)
    await state.update_data(user_id=message.from_user.id)

    for i in range(len(dayTimes)):
        builder.add(InlineKeyboardButton(text=dayTimes[i], callback_data=f"select_{i}"))

    builder.adjust(2)
    await message.answer(
        "Выберите дату из списка ниже:", reply_markup=builder.as_markup()
    )


@dp.callback_query(F.data.startswith("select_"), User.waiting_for_day)
async def process_selection_time(callback: types.CallbackQuery, state: FSMContext):
    date_id = int(callback.data.split("_")[1])
    selected_option = dayTimes[date_id]

    if selected_option == "Кастомное":
        await callback.answer()
        calendar = SimpleCalendar()
        now = datetime.now()
        calendar_markup = await calendar.start_calendar(year=now.year, month=now.month)
        await callback.message.edit_text(
            "Выберите дату на календаре:", reply_markup=calendar_markup
        )
        return

    now_date = datetime.now().date()
    if selected_option == "Сегодня":
        target_date = now_date
    elif selected_option == "Завтра":
        target_date = now_date + timedelta(days=1)
    elif selected_option == "Через неделю":
        target_date = now_date + timedelta(weeks=1)

    # Исправлено: сохраняем 'day' для текста подтверждения и 'day_iso' для БД
    await state.update_data(
        day=selected_option, day_iso=target_date.strftime("%Y-%m-%d")
    )
    await state.set_state(User.waiting_for_time)

    builder = InlineKeyboardBuilder()
    for i in range(len(timeTimes)):
        builder.add(InlineKeyboardButton(text=timeTimes[i], callback_data=f"time_{i}"))
    builder.adjust(2)

    await callback.answer(f"Вы выбрали: {selected_option}")
    await callback.message.edit_text(
        f"Вы выбрали день: {selected_option}\nТеперь выберите время:",
        reply_markup=builder.as_markup(),
    )


@dp.callback_query(SimpleCalendarCallback.filter(), User.waiting_for_day)
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
        for i in range(len(timeTimes)):
            builder.add(
                InlineKeyboardButton(text=timeTimes[i], callback_data=f"time_{i}")
            )
        builder.adjust(2)

        await callback.message.edit_text(
            f"Вы выбрали дату: {formatted_date}\nТеперь выберите время:",
            reply_markup=builder.as_markup(),
        )


@dp.callback_query(F.data.startswith("time_"), User.waiting_for_time)
async def process_selection_repetion(callback: types.CallbackQuery, state: FSMContext):
    time_id = int(callback.data.split("_")[1])
    selected_option = timeTimes[time_id]

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
    for i in range(len(repetionTimes)):
        builder.add(
            InlineKeyboardButton(text=repetionTimes[i], callback_data=f"repetion_{i}")
        )
    builder.adjust(2)

    await callback.answer(f"Вы выбрали: {selected_option}")
    await callback.message.edit_text(
        f"Вы выбрали время: {selected_option}\nТеперь выберите повторение:",
        reply_markup=builder.as_markup(),
    )


@dp.message(User.waiting_for_custom_time)
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
    for i in range(len(repetionTimes)):
        builder.add(
            InlineKeyboardButton(text=repetionTimes[i], callback_data=f"repetion_{i}")
        )
    builder.adjust(2)

    await message.answer(
        f"Вы выбрали время: в {formatted_time}\nТеперь выберите повторение:",
        reply_markup=builder.as_markup(),
    )


@dp.callback_query(F.data.startswith("repetion_"), User.waiting_for_repeat)
async def process_selection_text(callback: types.CallbackQuery, state: FSMContext):
    repetion_id = int(callback.data.split("_")[1])
    selected_option = repetionTimes[repetion_id]

    if selected_option == "Кастомное":
        await callback.answer()
        await state.set_state(User.waiting_for_custom_repeat)
        await callback.message.edit_text(
            "Введите интервал повторения в формате **ДД:ЧЧ:ММ**\n"
            "(где ДД — дни, ЧЧ — часы, ММ — минуты, например: `01:12:30`):",
            parse_mode="Markdown",
        )
        return

    # Используем timedelta вместо строк
    interval_map = {
        "Каждый день": timedelta(days=1),
        "Каждую неделю": timedelta(weeks=1),
        "Каждый месяц": timedelta(
            days=30
        ),  # В timedelta нет месяцев, используем 30 дней
    }

    await state.update_data(
        repetion=selected_option, repeat_interval=interval_map[selected_option]
    )
    await state.set_state(User.waiting_for_text)

    await callback.answer(f"Вы выбрали: {selected_option}")
    await callback.message.edit_text(
        f"Вы выбрали повторение: {selected_option}\nТеперь введите текст напоминания сообщением:"
    )


@dp.message(User.waiting_for_custom_repeat)
async def process_custom_repeat_input(message: types.Message, state: FSMContext):
    repeat_text = message.text.strip().replace(".", ":")

    if not re.match(r"^\d{2}:([01]\d|2[0-3]):[0-5]\d$", repeat_text):
        await message.answer(
            "Некорректный формат! Введите интервал в формате **ДД:ЧЧ:ММ** (например, `00:08:00`):",
            parse_mode="Markdown",
        )
        return

    days, hours, minutes = map(int, repeat_text.split(":"))

    # Создаем timedelta объект
    pg_interval = timedelta(days=days, hours=hours, minutes=minutes)
    selected_repeat = f"Каждые {days}д. {hours}ч. {minutes}мин."

    await state.update_data(repetion=selected_repeat, repeat_interval=pg_interval)
    await state.set_state(User.waiting_for_text)

    await message.answer(
        f"Вы выбрали повторение: {selected_repeat}\nТеперь введите текст напоминания сообщением:"
    )


@dp.message(User.waiting_for_text)
async def process_text_input(message: types.Message, state: FSMContext):
    text = message.text.strip()
    await state.update_data(text=text)
    await state.set_state(User.waiting_for_confirmation)

    user_data = await state.get_data()

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Подтвердить", callback_data="confirm_yes"))
    builder.add(InlineKeyboardButton(text="Отмена", callback_data="confirm_no"))
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


@dp.callback_query(F.data == "confirm_yes", User.waiting_for_confirmation)
async def process_confirm(callback: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()

    # Исправлено: раскомментировано получение day_iso и добавлена защита
    day_iso = user_data.get("day_iso")
    time_val = user_data.get("time_val")

    if not day_iso:
        day_str = user_data.get("day", "")
        if "сегодня" in day_str.lower():
            day_iso = datetime.now().strftime("%Y-%m-%d")
        elif "завтра" in day_str.lower():
            day_iso = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        elif "неделю" in day_str.lower():
            day_iso = (datetime.now() + timedelta(weeks=1)).strftime("%Y-%m-%d")
        else:
            try:
                parsed_date = datetime.strptime(day_str, "%d.%m.%Y")
                day_iso = parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                day_iso = datetime.now().strftime("%Y-%m-%d")

    if not time_val:
        time_str = user_data.get("time", "10:00").replace("в ", "").strip()
        time_val = time_str

    dt_string = f"{day_iso} {time_val}"
    target_datetime = datetime.strptime(dt_string, "%Y-%m-%d %H:%M")

    user_id = user_data["user_id"]
    repeat_interval = user_data.get("repeat_interval")
    message_text = user_data["text"]

    query = """
        INSERT INTO reminders (user_id, target_datetime, repeat_interval, message)
        VALUES ($1, $2, $3::interval, $4);
    """

    try:
        async with db_pool.acquire() as conn:
            await conn.execute(
                query,
                user_id,
                target_datetime,
                repeat_interval,
                message_text,
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


@dp.callback_query(F.data == "confirm_no", User.waiting_for_confirmation)
async def process_cancel(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer("Отменено")
    await callback.message.edit_text("❌ Создание напоминания отменено.")
    await state.clear()


async def set_main_menu(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="start_notification", description="Запустить notification"),
    ]
    await bot.set_my_commands(commands)


async def main():
    try:
        await init_db()
        print("БД успешно подключена!")

        # Установка команд меню
        await set_main_menu(bot)
        print("Бот запущен!")

        # Запускаем фоновую задачу
        asyncio.create_task(check_reminders(bot, db_pool))

        # Запуск поллинга
        await dp.start_polling(bot)
    finally:
        if db_pool:
            await db_pool.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
