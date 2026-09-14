import logging
from datetime import date, time

class Calendar: 
    def __init__(self, conn) -> None: 
        self.conn = conn 
        self.create_table() 

    def create_table(self) -> None: 
        """Создает таблицы events и users в базе данных, если их нет."""
        with self.conn.cursor() as cursor: 
            # Создание таблицы событий (она у тебя уже написана)
            cursor.execute(""" 
                CREATE TABLE IF NOT EXISTS events ( 
                    id serial PRIMARY KEY, 
                    user_id bigint NOT NULL,
                    name text NOT NULL, 
                    date date NOT NULL, 
                    time time NOT NULL,
                    details text
                ); 
            """)
            
            # 1. Пишем запрос на создание таблицы пользователей users.
            # Нам нужен первичный ключ id (будем хранить туда user_id из ВК)
            # и колонка registered_at для даты регистрации (с дефолтным значением NOW())
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id bigint PRIMARY KEY,
                    registered_at timestamp DEFAULT NOW()
                );
            """)
            
            self.conn.commit() 
            logging.info("Таблицы 'events' и 'users' успешно инициализированы.") 

    def register_user(self, user_id: int) -> bool:
        """
        Регистрирует пользователя в базе данных.
        Возвращает True, если регистрация успешна, и False, если пользователь уже был зарегистрирован.
        """
        with self.conn.cursor() as cursor:
            # 2. Сначала проверяем, есть ли уже такой пользователь в таблице users
            cursor.execute("SELECT id FROM users WHERE id = %s;", (user_id,))
            user = cursor.fetchone()
            
            if user is None:
                # 3. Если пользователя нет, пишем SQL-запрос INSERT INTO для добавления id в таблицу users
                cursor.execute("""
                    INSERT INTO users (id) 
                    VALUES (%s);
                """, (user_id,))
                
                # 4. Фиксируем изменения в БД с помощью метода commit у объекта self.conn
                self.conn.commit()
                logging.info(f"Пользователь {user_id} успешно зарегистрирован!")
                return True
                
            logging.info(f"Пользователь {user_id} уже существует в базе.")
            return False


    def create_event(self, user_id: int, event_name: str, event_date: date, event_time: time, event_details: str) -> None: 
        """Вставляет новое событие, сохраняя ID создателя."""
        with self.conn.cursor() as cursor: 
            # 2. Добавь колонку user_id в INSERT INTO и плейсхолдер %s
            cursor.execute(""" 
                INSERT INTO events (user_id, name, date, time, details) 
                VALUES (%s, %s, %s, %s, %s); 
            """, (user_id, event_name, event_date, event_time, event_details)) 
            
            self.conn.commit() 
            logging.info(f"Событие '{event_name}' записано для пользователя {user_id}!") 

    def read_event(self, user_id: int, event_name: str) -> list[tuple]: 
        """Ищет конкретное событие ТОЛЬКО среди записей этого пользователя."""
        with self.conn.cursor() as cursor: 
            # 3. Допиши условие AND, чтобы чужие события с таким же именем не выводились
            cursor.execute(""" 
                SELECT id, name, date, time, details FROM events 
                WHERE name = %s AND user_id = %s; 
            """, (event_name, user_id)) 
            
            return cursor.fetchall() 

    def display_events(self, user_id: int) -> list[tuple]: 
        """Выводит ВСЕ события конкретного пользователя ВК."""
        with self.conn.cursor() as cursor: 
            # 4. Напиши условие WHERE, чтобы выбрать записи только текущего user_id
            cursor.execute(""" 
                SELECT id, name, date, time, details FROM events 
                WHERE user_id = %s 
                ORDER BY date, time; 
            """, (user_id,)) 
            
            return cursor.fetchall()

    def edit_event(self, user_id: int, event_name: str, new_date=None, new_description=None) -> None:
        """Метод для ИЗМЕНЕНИЯ строк таблицы events по имени события и ID пользователя."""
        with self.conn.cursor() as cursor:
            # 1. Если передана новая дата, обновляем её в базе данных для текущего пользователя
            if new_date is not None:
                cursor.execute("""
                    UPDATE events 
                    SET date = %s 
                    WHERE name = %s AND user_id = %s;
                """, (new_date, event_name, user_id))
                
            # 2. Если передано новое описание (details), обновляем его в базе данных
            # Напиши SQL-запрос UPDATE аналогично первому, используя плейсхолдеры %s
            if new_description is not None:
                cursor.execute("""
                    UPDATE events 
                    SET details = %s 
                    WHERE name = %s AND user_id = %s;
                """, (new_description, event_name, user_id))
                
            self.conn.commit()
            logging.info(f"Событие '{event_name}' успешно отредактировано для {user_id}!")

    def delete_event(self, user_id: int, event_name: str) -> None:
        """Метод для УДАЛЕНИЯ строки таблицы events по имени события и ID пользователя."""
        with self.conn.cursor() as cursor:
            # 3. Напиши SQL-запрос DELETE, чтобы удалить записи, 
            # где совпадает и имя события, и ID пользователя (user_id)
            cursor.execute("""
                DELETE FROM events 
                WHERE name = %s AND user_id = %s;
            """, (event_name, user_id))
            
            self.conn.commit()
            logging.info(f"Событие '{event_name}' успешно удалено для {user_id}!")
