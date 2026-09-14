import logging
from datetime import date, time

class Calendar:
    """
    Класс для управления событиями календаря напрямую через базу данных PostgreSQL.
    """
    def __init__(self, conn) -> None:
        # 1. Сохраняем объект соединения с БД, который нам передадут извне
        self.conn = conn
        # Сразу проверяем и создаем таблицу при инициализации класса
        self.create_table()

    def create_table(self) -> None:
        """Создает таблицу events в базе данных, если её нет."""
        with self.conn.cursor() as cursor:
            # 2. Перенеси сюда SQL-запрос из пункта 6 на скриншоте.
            # Не забудь добавить фразу IF NOT EXISTS после CREATE TABLE, чтобы код не падал при повторном запуске!
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id serial PRIMARY KEY,
                    name text NOT NULL,
                    date date NOT NULL,
                    time time NOT NULL
                );
            """)
            # Подсказка: для фиксации создания таблицы нам нужен метод commit
            self.conn.commit()
            logging.info("Таблица 'events' успешно инициализирована в PostgreSQL.")

    def create_event(self, event_name: str, event_date: date, event_time: time) -> None:
        """Вставляет новое событие в таблицу events."""
        with self.conn.cursor() as cursor:
            # 3. Пишем SQL-запрос на добавление строки.
            # Используем плейсхолдеры %s для безопасной вставки данных
            cursor.execute("""
                INSERT INTO events (name, date, time) 
                VALUES (%s, %s, %s);
            """, (event_name, event_date, event_time))
            
            # Фиксируем изменения в базе данных
            self.conn.commit()
            logging.info(f"Событие '{event_name}' успешно записано в БД PostgreSQL!")
