import asyncio
import logging
import psycopg2
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from settings.config import AppSettings
from app.calendar import Calendar
from app.handlers.commands import (
    add_calendar_event_handler,
    register_user_handler,
    edit_calendar_event_handler,
    delete_calendar_event_handler
)

from app.handlers.commands import (
    add_calendar_event_handler,
    register_user_handler,
    edit_calendar_event_handler,
    delete_calendar_event_handler,
    start_create_event_handler,
    get_main_keyboard
)
import json


class Application:
    def __init__(self, app_settings: AppSettings) -> None:
        self.settings = app_settings
        token_str = self.settings.VK_API_KEY.get_secret_value()
        self.vk_session = vk_api.VkApi(token=token_str)
        self.vk = self.vk_session.get_api()
        self.longpoll = None

        # Подключаемся к базе данных PostgreSQL
        self.conn = psycopg2.connect(
            host=self.settings.DB_HOST,
            database=self.settings.DB_NAME,
            user=self.settings.DB_USER,
            password=self.settings.DB_PASSWORD.get_secret_value()
        )

        # Передаем соединение в наш календарь
        self.calendar = Calendar(conn=self.conn)

        self.user_states = {}

        logging.info("Бот-Календарь успешно инициализирован.")

    async def run(self) -> None:
        logging.info("Запуск поллинга...")
        self.longpoll = VkLongPoll(self.vk_session)
        logging.info("Бот слушает сообщения!")
        while True:
            await asyncio.sleep(0.05)

            events = self.longpoll.check()
            if events:
                for event in events:
                    if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                        user_id = event.user_id
                        user_text = event.text.lower().strip()

                        # ВК передает payload в объекте event.extra_values в виде строки
                        payload_data = None
                        if hasattr(event, 'extra_values') and event.extra_values.get('payload'):
                            try:
                                payload_data = json.loads(
                                    event.extra_values['payload'])
                            except Exception:
                                pass

                        logging.info(
                            f"Получено сообщение: '{event.text}', payload: {payload_data} от {user_id}")

                        # ----------------------------------------------------
                        # БЛОК 1: ОБРАБОТКА ФИКСИРОВАННЫХ КОМАНД И ГЛАВНЫХ КНОПОК
                        # ----------------------------------------------------

                        if user_text == "регистрация":
                            await register_user_handler(vk=self.vk, user_id=user_id, calendar=self.calendar)

                        elif user_text == "создать заметку":
                            self.user_states[user_id] = {
                                "state": "WAITING_FOR_DATE"}
                            await start_create_event_handler(vk=self.vk, user_id=user_id)

                        # 1. Привязываем кнопку "Показать все заметки"
                        elif user_text == "показать все заметки":
                            # Вызываем метод чтения из нашего класса calendar
                            records = self.calendar.display_events(
                                user_id=user_id)

                            if not records:
                                reply = "📅 У вас пока нет запланированных заметок."
                            else:
                                lines = []
                                # Из базы прилетают кортежи: (id, name, date, time, details)
                                for _, name, event_date, event_time, _ in records:
                                    lines.append(
                                        f"📌 {event_date} в {event_time} — *{name}*")
                                reply = "📋 Ваши текущие заметки:\n" + \
                                    "\n".join(lines)

                            self.vk.messages.send(
                                user_id=user_id, message=reply, random_id=0)

                        elif user_text == "изменить заметку":
                            # 1. Запрашиваем все заметки пользователя из базы
                            records = self.calendar.display_events(
                                user_id=user_id)

                            if not records:
                                self.vk.messages.send(
                                    user_id=user_id,
                                    message="📅 У вас пока нет заметок для изменения.",
                                    random_id=0
                                )
                            else:
                                lines = []
                                # Создаем временный список для хранения реальных ID заметок из СУБД
                                # Индекс в этом списке + 1 будет равен порядковому номеру для пользователя
                                db_ids = []

                                for index, (event_id, name, event_date, event_time, _) in enumerate(records):
                                    db_ids.append(event_id)
                                    lines.append(
                                    f"{index + 1}. 📌 {event_date} в {event_time} — *{name}*")

                                # Переводим пользователя в режим ожидания номера заметки
                                # Сохраняем массив с ID, чтобы потом по индексу вытащить нужный id из базы
                                self.user_states[user_id] = {
                                    "state": "WAITING_FOR_EDIT_NUMBER",
                                    "db_ids": db_ids
                                }

                                reply = "📝 Выберите номер заметки, которую хотите изменить:\n\n" + \
                                    "\n".join(lines)
                                self.vk.messages.send(
                                    user_id=user_id,
                                    message=reply,
                                    keyboard=get_main_keyboard(),  # Оставляем меню или кнопку Отмена
                                    random_id=0
                                )

                        # 3. Привязываем кнопку "Удалить заметку"
                        elif user_text == "Удалить заметку":
                            self.vk.messages.send(
                                user_id=user_id,
                                message="⌨️ Чтобы удалить заметку, введите в чат:\nудалить Название",
                                random_id=0
                            )

                        # ----------------------------------------------------
                        # БЛОК 2: АВТОМАТИЧЕСКАЯ МАШИНА СОСТОЯНИЙ (FSM)
                        # ----------------------------------------------------
                        elif user_id in self.user_states:
                            current_user_state = self.user_states[user_id]["state"]
                            
                             # ШАГ ИЗМЕНЕНИЯ 0: Бот ждал номер заметки
                            if current_user_state == "WAITING_FOR_EDIT_NUMBER":
                                try:
                                    # Переводим ввод пользователя в числовой индекс
                                    chosen_index = int(event.text.strip()) - 1
                                    saved_ids = self.user_states[user_id]["db_ids"]
                                    
                                    if chosen_index < 0 or chosen_index >= len(saved_ids):
                                        raise ValueError("Неверный номер")
                                        
                                    # Вытаскиваем реальный ID из базы данных
                                    target_event_id = saved_ids[chosen_index]
                                    
                                    # Записываем ID в стейт и переключаем на сбор новой даты
                                    self.user_states[user_id]["edit_event_id"] = target_event_id
                                    self.user_states[user_id]["state"] = "EDIT_WAITING_FOR_DATE"
                                    
                                    # Сразу импортируем и вызываем нашу готовую клавиатуру дат (Сегодня/Завтра)
                                    from app.handlers.commands import get_date_keyboard
                                    self.vk.messages.send(
                                        user_id=user_id,
                                        message="📅 Отлично! Шаг 1: Выберите НОВУЮ дату для этой заметки или введите её вручную (ГГГГ-ММ-ДД):",
                                        keyboard=get_date_keyboard(),
                                        random_id=0
                                    )
                                except ValueError:
                                    self.vk.messages.send(
                                        user_id=user_id,
                                        message="❌ Ошибка! Пожалуйста, введите корректный номер заметки из списка выше:",
                                        random_id=0
                                    )

                            # ШАГ ИЗМЕНЕНИЯ 1: Бот ждал новую дату
                            elif current_user_state == "EDIT_WAITING_FOR_DATE":
                                if user_text == "ввести вручную":
                                    self.vk.messages.send(
                                        user_id=user_id,
                                        message="⌨️ Введите дату вручную (ГГГГ-ММ-ДД):",
                                        random_id=0
                                    )
                                    pass
                                else:
                                    if payload_data and payload_data.get("command") == "create_event_date":
                                        chosen_date = payload_data["date"]
                                    else:
                                        chosen_date = event.text.strip()
                                        
                                    self.user_states[user_id]["new_date"] = chosen_date
                                    self.user_states[user_id]["state"] = "EDIT_WAITING_FOR_TIME"
                                    
                                    self.vk.messages.send(
                                        user_id=user_id,
                                        message=f"📅 Новая дата '{chosen_date}' принята!\n⏰ Шаг 2: Теперь введите НОВОЕ время события (ЧЧ:ММ):",
                                        random_id=0
                                    )

                            # ШАГ ИЗМЕНЕНИЯ 2: Бот ждал новое время
                            elif current_user_state == "EDIT_WAITING_FOR_TIME":
                                chosen_time = event.text.strip()
                                self.user_states[user_id]["new_time"] = chosen_time
                                self.user_states[user_id]["state"] = "EDIT_WAITING_FOR_NAME"
                                
                                self.vk.messages.send(
                                    user_id=user_id,
                                    message=f"⏰ Новое время '{chosen_time}' записано!\n📝 Шаг 3: Введите НОВОЕ название для этого события:",
                                    random_id=0
                                )

                            # ШАГ ИЗМЕНЕНИЯ 3: Финал — бот получил новое название и обновляет БД
                            elif current_user_state == "EDIT_WAITING_FOR_NAME":
                                new_name = event.text.strip()
                                
                                # Извлекаем всё, что бережно копили в стейте
                                event_id = self.user_states[user_id]["edit_event_id"]
                                saved_date = self.user_states[user_id]["new_date"]
                                saved_time = self.user_states[user_id]["new_time"]
                                
                                # Парсим типы данных для нашей СУБД PostgreSQL
                                from datetime import date as dt_date, time as dt_time
                                parsed_date = dt_date.fromisoformat(saved_date)
                                parsed_time = dt_time.fromisoformat(saved_time)
                                
                                # 2. Вызываем твой новый точечный метод обновления по ID!
                                self.calendar.update_event_by_id(
                                    event_id=event_id,
                                    user_id=user_id,
                                    new_name=new_name,
                                    new_date=parsed_date,
                                    new_time=parsed_time
                                )
                                
                                # Очищаем стейт пользователя, финал!
                                self.user_states.pop(user_id, None)
                                
                                self.vk.messages.send(
                                    user_id=user_id,
                                    message="✅ Заметка успешно обновлена в вашей базе данных!",
                                    keyboard=get_main_keyboard(),
                                    random_id=0
                                )

                            # ШАГ 1: Бот ждал дату, и пользователь её предоставил
                            elif current_user_state == "WAITING_FOR_DATE":
                                # Проверяем, нажал ли пользователь текстовую кнопку "Ввести вручную"
                                if user_text == "ввести вручную":
                                    self.vk.messages.send(
                                        user_id=user_id,
                                        message="⌨️ Пожалуйста, введите дату вручную сообщением в формате ГГГГ-ММ-ДД (например: 2026-09-15):",
                                        random_id=0
                                    )
                                    # Специальное ключевое слово pass, чтобы бот просто пропустил этот шаг
                                    # и не переключал состояние, продолжая ждать нормальную дату
                                    pass

                                else:
                                    # Проверяем, нажал ли интерактивную кнопку (Сегодня/Завтра)
                                    if payload_data and payload_data.get("command") == "create_event_date":
                                        chosen_date = payload_data["date"]
                                    else:
                                        # Если ввел дату цифрами вручную сообщением
                                        chosen_date = event.text.strip()

                                    # Сохраняем дату в стейт и переводим на следующий шаг — ожидание времени
                                    self.user_states[user_id]["date"] = chosen_date
                                    self.user_states[user_id]["state"] = "WAITING_FOR_TIME"

                                    self.vk.messages.send(
                                        user_id=user_id,
                                        message=f"📅 Дата '{chosen_date}' успешно выбрана!\n⏰ Шаг 2: Теперь введите время события в формате ЧЧ:ММ (например, 15:30):",
                                        random_id=0
                                    )

                            # ШАГ 2: Бот ждал время
                            elif current_user_state == "WAITING_FOR_TIME":
                                chosen_time = event.text.strip()

                                # Сохраняем время в стейт и переходим к шагу 3 — название
                                self.user_states[user_id]["time"] = chosen_time
                                self.user_states[user_id]["state"] = "WAITING_FOR_NAME"

                                self.vk.messages.send(
                                    user_id=user_id,
                                    message=f"⏰ Время '{chosen_time}' записано!\n📝 Шаг 3: Введите название (текст) вашего события:",
                                    random_id=0
                                )

                            # ШАГ 3: Финальный шаг — бот получил название события
                            elif current_user_state == "WAITING_FOR_NAME":
                                event_name = event.text.strip()

                                # Достаем из сохраненного стейта ранее выбранные дату и время
                                saved_date = self.user_states[user_id]["date"]
                                saved_time = self.user_states[user_id]["time"]

                                # Вызываем наш готовый хэндлер сохранения в PostgreSQL!
                                await add_calendar_event_handler(
                                    vk=self.vk,
                                    user_id=user_id,
                                    date_str=saved_date,
                                    time_str=saved_time,
                                    text=event_name,
                                    calendar=self.calendar
                                )

                                # Обязательно удаляем стейт пользователя, так как процесс успешно завершен!
                                self.user_states.pop(user_id, None)

                                # Возвращаем пользователю главную клавиатуру меню
                                self.vk.messages.send(
                                    user_id=user_id,
                                    message="📋 Что хотите сделать дальше?",
                                    keyboard=get_main_keyboard(),
                                    random_id=0
                                )
