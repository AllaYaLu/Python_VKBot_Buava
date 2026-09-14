import vk_api
import random
import logging
# 1. Импортируй класс time из модуля datetime вместе с date
from datetime import date, time
from app.calendar import Calendar

async def add_calendar_event_handler(
    vk, user_id: int, date_str: str, time_str: str, text: str, calendar: Calendar
) -> None:
    """
    Обработчик для добавления заметки на КОНКРЕТНУЮ дату и время в PostgreSQL.
    """
    try:
        # Превращаем строки в объекты даты и времени
        event_date = date.fromisoformat(date_str.strip())
        # 2. Вызови метод time.fromisoformat() и передай туда time_str.strip()
        event_time = time.fromisoformat(time_str.strip())
        
        # 3. Вызываем наш новый метод create_event у объекта calendar.
        # Передай туда три параметра: event_name, event_date и event_time
        calendar.create_event(
            event_name=text,
            event_date=event_date,
            event_time=event_time
        )
        
        reply_message = f"📅 Событие '{text}' успешно сохранено в БД на {event_date} в {time_str}!"
        
        vk.messages.send(
            user_id=user_id,
            message=reply_message,
            random_id=random.randint(1, 2**31 - 1)
        )
    except ValueError:
        vk.messages.send(
            user_id=user_id,
            message="❌ Ошибка! Формат: событие ГГГГ-ММ-ДД ЧЧ:ММ Текст (например: событие 2026-09-14 15:00 Кофе)",
            random_id=random.randint(1, 2**31 - 1)
        )
