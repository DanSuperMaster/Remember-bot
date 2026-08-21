import os
import re

import telebot
from telebot import types
from dotenv import load_dotenv



load_dotenv("ApiKeyFile.env")
bot = telebot.TeleBot(os.getenv("API_KEY"))

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "Это бот, который создан для того, чтобы напоминать о чём-то "
                                      "(пока это будет просто бот, возможно в будущем появится сайт "
                                      "(может он уже появился))")


@bot.message_handler(content_types=['text'])
def get_text(message):
    chat_id = message.chat.id       # ID чата, откуда пришло сообщение
    user_text = message.text        # Текст самого сообщения
    user_name = message.from_user.first_name # Имя отправителя


def extract_patterns(text):

    result = {'time': [], 'date': [], 'local_days': [], 'from_time': [], 'regular': []}

    patterns = [
        (r'\d{1,2}[.]\d{1,2}[.]\d{2,4}', 'date'),
        (r'\d{1,2}[:;.\-]\d{2}', 'time'),
        (r'завтра|послезавтра', 'local_days'),
        (r'через\s+\d+\s+(минут|час|день|месяц|год)', 'from_time'),
        (r'каждый\s+\S+', 'regular')
    ]

    for pattern, key in patterns:
        if key == 'date':
            result[key].extend(re.findall(pattern, text, re.IGNORECASE))
        if key not in ['date', 'time']:
            result[key].extend(re.findall(pattern, text, re.IGNORECASE))

    clean_text = text
    for date in result['date']:
        clean_text = clean_text.replace(date, '<<DATE>>')

    for pattern, key in patterns:
        if key == 'time':
            result[key].extend(re.findall(pattern, clean_text, re.IGNORECASE))

    all_markers_with_context = []
    context_keywords = ['до', 'с', 'по', 'от', 'в', 'во']

    for key in ['date', 'time', 'local_days', 'from_time', 'regular']:
        for marker in result[key]:
            pos = text.find(marker)

            before = text[max(0, pos - 3):pos].strip()

            context = None
            for kw in context_keywords:
                if before == kw:
                    context = kw
                    break

            all_markers_with_context.append({
                'marker': marker,
                'type': key,
                'context': context
            })

    return all_markers_with_context


text = "Напомни купить молоко завтра в 15.30 и каждый понедельник до 31.08.27"
markers = extract_patterns(text)
print(markers)







bot.infinity_polling()