import asyncio

from aiogram import Bot
from aiogram.types import BotCommand

from config import bot, dp
from db import db_pool, init_db
from handlers import router
from tasks import check_reminders


async def set_main_menu(bot_instance: Bot):
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="start_notification", description="Запустить notification"),
    ]
    await bot_instance.set_my_commands(commands)


async def main():
    try:
        await init_db()
        print("БД успешно подключена!")

        await set_main_menu(bot)
        print("Бот запущен!")

        dp.include_router(router)

        asyncio.create_task(check_reminders(bot))

        await dp.start_polling(bot)
    finally:
        if db_pool:
            await db_pool.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
