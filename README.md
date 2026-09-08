# Reminder Telegram Bot

@reminder_dsm_bot

Асинхронный Telegram-бот для создания и отслеживания регулярных и разовых напоминаний. Написан на Python с использованием **aiogram 3** и **asyncpg** (PostgreSQL).

---

## 🛠 Технологический стек

* **Python 3.14**
* **aiogram 3.x** — асинхронный фреймворк для Telegram Bot API
* **PostgreSQL + asyncpg** — база данных и асинхронный драйвер

---

## 📁 Структура проекта

```text
reminder_bot/
│
├── config.py             # Настройки приложения и инициализация Bot/Dispatcher
├── db.py                 # Подключение к PostgreSQL и работы с БД
├── states.py             # FSM-состояния (StatesGroup)
├── keyboards.py          # Reply и Inline клавиатуры
├── handlers.py           # Обработчики команд, кнопок и текстовых сообщений
├── tasks.py              # Фоновые задачи (проверка и отправка напоминаний)
├── main.py               # Точка входа в приложение
├── ApiKeyFile.env        # Конфигурационный файл с ключами (не коммитится)
└── README.md             # Документация проекта
