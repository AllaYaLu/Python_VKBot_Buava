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

                        logging.info(
                            f"Получено сообщение: '{event.text}' от {user_id}")

                        # Твоя прошлая команда для добавления события
                        if user_text.startswith("событие"):
                            clean_payload = event.text[8:].strip()
                            try:
                                date_str, time_str, text_str = clean_payload.split(
                                    maxsplit=2)
                                await add_calendar_event_handler(
                                    vk=self.vk,
                                    user_id=user_id,
                                    date_str=date_str,
                                    time_str=time_str,
                                    text=text_str,
                                    calendar=self.calendar
                                )
                            except ValueError:
                                self.vk.messages.send(
                                    user_id=user_id,
                                    message="❌ Ошибка! Напишите: событие ГГГГ-ММ-ДД ЧЧ:ММ Текст",
                                    random_id=0
                                )

                        # 2. Наше новое условие для регистрации!
                        # Проверяем, равен ли user_text строке "регистрация"
                        elif user_text == "регистрация":
                            # 3. Вызови асинхронный register_user_handler через await
                            # Передай туда 3 параметра: vk=self.vk, user_id=user_id и calendar=self.calendar
                            await register_user_handler(
                                vk=self.vk,
                                user_id=user_id,
                                calendar=self.calendar
                            )
                            
                             # Ветка изменения
                        elif user_text.startswith("изменить"):
                            payload = event.text[8:].strip() # Отрезаем слово "изменить"
                            await edit_calendar_event_handler(
                                vk=self.vk,
                                user_id=user_id,
                                payload=payload,
                                calendar=self.calendar
                            )

                        # Ветка удаления
                        elif user_text.startswith("удалить"):
                            event_name = event.text[7:].strip() # Отрезаем слово "удалить"
                            await delete_calendar_event_handler(
                                vk=self.vk,
                                user_id=user_id,
                                event_name=event_name,
                                calendar=self.calendar
                            )