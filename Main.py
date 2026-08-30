import os
import re
from datetime import datetime, timedelta
import dateparser
import spacy
import telebot
from spacy.matcher import Matcher

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




'''def extract_with_spacy(text):
    """
    Извлекает даты, время, числа из текста с помощью spaCy
    """
    doc = nlp(text)

    result = {
        'dates': [],
        'times': [],
        'numbers': [],
        'tokens': [],
        'entities': []
    }

    # Собираем все сущности
    for ent in doc.ents:
        result['entities'].append({
            'text': ent.text,
            'label': ent.label_,
            'start': ent.start_char,
            'end': ent.end_char
        })

        if ent.label_ == 'DATE':
            result['dates'].append(ent.text)
        elif ent.label_ == 'TIME':
            result['times'].append(ent.text)

    # Собираем токены (слова) с их частями речи
    for token in doc:
        result['tokens'].append({
            'text': token.text,
            'lemma': token.lemma_,  # начальная форма
            'pos': token.pos_,  # часть речи
            'dep': token.dep_  # синтаксическая роль
        })

        # Если это число
        if token.pos_ == 'NUM':
            result['numbers'].append(token.text)

    return result'''


nlp = spacy.load("ru_core_news_sm")


def parse_with_spacy_fixed(text):
    """
    Парсер на основе spaCy с минимальным использованием регулярок
    """
    doc = nlp(text)

    # Создаем матчер для расширенного поиска
    matcher = Matcher(nlp.vocab)

    # 1. Собираем даты и время из сущностей
    date_parts = []
    time_parts = []
    date_entities = []
    time_entities = []

    for ent in doc.ents:
        if ent.label_ == 'DATE':
            date_parts.append(ent.text)
            date_entities.append(ent)
        elif ent.label_ == 'TIME':
            time_parts.append(ent.text)
            time_entities.append(ent)

    # 2. Обработка точных дат и времени
    if date_parts or time_parts:
        full_str = ' '.join(date_parts + time_parts)

        # Проверяем наличие предлога "в" между датой и временем
        if date_parts and time_parts:
            # Находим позиции в тексте
            date_end = date_entities[-1].end_char if date_entities else 0
            time_start = time_entities[0].start_char if time_entities else 0

            # Проверяем, есть ли "в" между ними
            between = text[date_end:time_start] if date_end < time_start else ""
            if "в" in between:
                full_str = f"{date_parts[-1]} в {time_parts[0]}"
            else:
                full_str = f"{date_parts[-1]} {time_parts[0]}"

        parsed = dateparser.parse(full_str, languages=['ru'])
        if parsed:
            return {
                'when': parsed,
                'type': 'exact',
                'date_str': ' '.join(date_parts),
                'time_str': ' '.join(time_parts),
                'text': text
            }

    # 3. Поиск дат через паттерны spaCy
    # 3.1. Дата с точками (25.12.2025) - используем токены
    date_pattern = [
        [{"SHAPE": "dd.dd.dddd"}],
        [{"SHAPE": "dd.dd.dd"}]
    ]
    matcher.add("DATE_DOTTED", date_pattern)

    matches = matcher(doc)
    for match_id, start, end in matches:
        span = doc[start:end]
        date_str = span.text

        # Ищем время рядом (через сущности TIME или через токены)
        time_match = None
        for token in doc:
            if token.ent_type_ == "TIME":
                time_match = token.text
                break

        # Если не нашли TIME сущность, ищем по шаблону времени
        if not time_match:
            for ent in doc.ents:
                if ent.label_ == "TIME":
                    time_match = ent.text
                    break

        if time_match:
            full_str = f"{date_str} {time_match}"
            parsed = dateparser.parse(full_str, languages=['ru'])
            if parsed:
                return {
                    'when': parsed,
                    'type': 'exact',
                    'date_str': date_str,
                    'time_str': time_match,
                    'text': text
                }
        else:
            parsed = dateparser.parse(date_str, languages=['ru'])
            if parsed:
                return {
                    'when': parsed,
                    'type': 'date_only',
                    'date_str': date_str,
                    'text': text
                }

    # 4. Поиск относительных дат (завтра, послезавтра)
    # Используем леммы для поиска
    tomorrow = False
    day_after_tomorrow = False

    for token in doc:
        if token.lemma_ in ['завтра', 'завтрашний']:
            tomorrow = True
        elif token.lemma_ in ['послезавтра']:
            day_after_tomorrow = True

    if tomorrow or day_after_tomorrow:
        # Ищем время через сущности TIME
        time_match = None
        for ent in doc.ents:
            if ent.label_ == "TIME":
                time_match = ent.text
                break

        if not time_match:
            # Ищем время через токены
            for token in doc:
                # Проверяем, похоже ли на время (цифры и двоеточие)
                if token.shape_ == "dd:dd" or token.shape_ == "dd.dd":
                    time_match = token.text
                    break

        if tomorrow:
            full_str = f"завтра {time_match if time_match else '10:00'}"
        else:
            full_str = f"послезавтра {time_match if time_match else '10:00'}"

        parsed = dateparser.parse(full_str, languages=['ru'])
        if parsed:
            return {
                'when': parsed,
                'type': 'soon',
                'text': text
            }

    # 5. Поиск относительных интервалов (через X минут/часов/дней)
    # Используем синтаксический анализ для поиска конструкций "через X"
    for token in doc:
        if token.lemma_ == 'через' and token.dep_ == 'case':
            # Ищем числительное после предлога
            for child in token.children:
                if child.pos_ == 'NUM':
                    count = int(child.text)
                    # Ищем единицу измерения
                    unit_token = None
                    for child2 in child.children:
                        if child2.pos_ == 'NOUN' and child2.lemma_ in ['минута', 'час', 'день', 'месяц', 'год']:
                            unit_token = child2
                            break

                    if unit_token:
                        unit = unit_token.lemma_
                        delta = None

                        if unit in ['минута']:
                            delta = timedelta(minutes=count)
                        elif unit in ['час']:
                            delta = timedelta(hours=count)
                        elif unit in ['день']:
                            delta = timedelta(days=count)
                        elif unit in ['месяц']:
                            delta = timedelta(days=count * 30)
                        elif unit in ['год']:
                            delta = timedelta(days=count * 365)

                        if delta:
                            return {
                                'when': datetime.now() + delta,
                                'type': 'relative',
                                'text': text
                            }

    # 6. Поиск повторяющихся событий
    recurring = False
    for token in doc:
        if token.lemma_ in ['каждый', 'еженедельный', 'ежедневный']:
            recurring = True
            break

    if recurring:
        # Ищем день недели через сущности или леммы
        weekdays = {
            'понедельник': 'monday',
            'вторник': 'tuesday',
            'среда': 'wednesday',
            'четверг': 'thursday',
            'пятница': 'friday',
            'суббота': 'saturday',
            'воскресенье': 'sunday'
        }

        found_day = None
        for token in doc:
            if token.lemma_ in weekdays:
                found_day = token.lemma_
                break

        # Ищем время через сущности TIME или токены
        hour, minute = 10, 0
        time_match = None

        for ent in doc.ents:
            if ent.label_ == "TIME":
                time_match = ent.text
                break

        if not time_match:
            for token in doc:
                if token.shape_ == "dd:dd" or token.shape_ == "dd.dd":
                    time_match = token.text
                    break

        if time_match:
            # Пробуем разные разделители
            for sep in [':', '.', ';', '-']:
                if sep in time_match:
                    parts = time_match.split(sep)
                    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                        hour, minute = int(parts[0]), int(parts[1])
                        break

        if found_day:
            return {
                'when': None,
                'type': 'recurring',
                'recurring_type': 'weekly',
                'weekday': weekdays.get(found_day, found_day),
                'hour': hour,
                'minute': minute,
                'text': text
            }
        else:
            # Ежедневное повторение
            return {
                'when': None,
                'type': 'recurring',
                'recurring_type': 'daily',
                'hour': hour,
                'minute': minute,
                'text': text
            }

    # 7. Только время (сегодня)
    time_match = None
    for ent in doc.ents:
        if ent.label_ == "TIME":
            time_match = ent.text
            break

    if not time_match:
        for token in doc:
            if token.shape_ == "dd:dd" or token.shape_ == "dd.dd":
                time_match = token.text
                break

    if time_match:
        for sep in [':', '.', ';', '-']:
            if sep in time_match:
                parts = time_match.split(sep)
                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                    hour, minute = int(parts[0]), int(parts[1])
                    now = datetime.now()
                    when = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if when < now:
                        when += timedelta(days=1)
                    return {
                        'when': when,
                        'type': 'time_only',
                        'text': text
                    }

    # 8. ДЕФОЛТ
    now = datetime.now()
    when = now.replace(hour=10, minute=0, second=0, microsecond=0)
    if when < now:
        when += timedelta(days=1)

    return {
        'when': when,
        'type': 'default',
        'text': text,
        'message': 'Установлено на завтра 10:00 (по умолчанию)'
    }


def format_result(result):
    """Форматирует результат для вывода"""
    if result['type'] == 'recurring':
        if result['recurring_type'] == 'daily':
            return f"🔄 Ежедневно в {result['hour']:02d}:{result['minute']:02d}"
        else:
            weekday_ru = {
                'monday': 'понедельник',
                'tuesday': 'вторник',
                'wednesday': 'среда',
                'thursday': 'четверг',
                'friday': 'пятница',
                'saturday': 'суббота',
                'sunday': 'воскресенье'
            }
            day = result.get('weekday', '')
            if day in weekday_ru:
                day = weekday_ru[day]
            return f"🔄 Каждый {day} в {result['hour']:02d}:{result['minute']:02d}"
    elif result.get('when'):
        return f"⏰ {result['when'].strftime('%d.%m.%Y %H:%M')}"
    else:
        return result.get('message', 'Не удалось распарсить')


# === ТЕСТ ===
if __name__ == "__main__":
    test_texts = [
        "Напомни купить молоко завтра в 15:30",
        "Встреча 31 августа 2025 в 14:30",
        "Позвонить через 5 минут",
        "Каждый понедельник в 11:00",
        "Сделать заказ до 25.12.2025",
        "Напомни выключить свет",
        "Встреча в 15:30",
        "Каждый день в 08:00",
        "Напомни через 2 часа",
        "Послезавтра в 12:00"
    ]

    print("=" * 60)
    print("ТЕСТИРОВАНИЕ ИСПРАВЛЕННОГО ПАРСЕРА")
    print("=" * 60)

    for text in test_texts:
        print(f"\n📝 {text}")
        result = parse_with_spacy_fixed(text)
        print(f"   Тип: {result['type']}")
        print(f"   Результат: {format_result(result)}")
        if result.get('message'):
            print(f"   Сообщение: {result['message']}")


bot.infinity_polling()