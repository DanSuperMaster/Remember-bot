import os
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

load_dotenv("ApiKeyFile.env")

MOSCOW_TZ = ZoneInfo("Europe/Moscow")

BOT_TOKEN = os.getenv("API_KEY")
DB_USER = os.getenv("POSTGRES_USER")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
DB_NAME = os.getenv("POSTGRES_DB")
DB_HOST = "localhost"
DB_PORT = 16500

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
