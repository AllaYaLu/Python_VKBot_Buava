import logging
from datetime import date, time

class Calendar: 
    def __init__(self, conn) -> None: 
        self.conn = conn 
        self.create_table() 

    def create_table(self) -> None: 
        """Создает таблицы events и users в базе данных, если их нет."""
        with self.conn.cursor() as cursor: 

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
            cursor.execute("SELECT id FROM users WHERE id = %s;", (user_id,))
            user = cursor.fetchone()
            
            if user is None:
                cursor.execute("""
                    INSERT INTO users (id) 
                    VALUES (%s);
                """, (user_id,))
                

                self.conn.commit()
                logging.info(f"Пользователь {user_id} успешно зарегистрирован!")
                return True
                
            logging.info(f"Пользователь {user_id} уже существует в базе.")
            return False


    def create_event(self, user_id: int, event_name: str, event_date: date, event_time: time, event_details: str) -> None: 
        """Вставляет новое событие, сохраняя ID создателя."""
        with self.conn.cursor() as cursor: 
            cursor.execute(""" 
                INSERT INTO events (user_id, name, date, time, details) 
                VALUES (%s, %s, %s, %s, %s); 
            """, (user_id, event_name, event_date, event_time, event_details)) 
            
            self.conn.commit() 
            logging.info(f"Событие '{event_name}' записано для пользователя {user_id}!") 

    def read_event(self, user_id: int, event_name: str) -> list[tuple]: 
        """Ищет конкретное событие ТОЛЬКО среди записей этого пользователя."""
        with self.conn.cursor() as cursor: 
     
            cursor.execute(""" 
                SELECT id, name, date, time, details FROM events 
                WHERE name = %s AND user_id = %s; 
            """, (event_name, user_id)) 
            
            return cursor.fetchall() 

    def display_events(self, user_id: int) -> list[tuple]: 
        """Выводит ВСЕ события конкретного пользователя ВК."""
        with self.conn.cursor() as cursor: 
      
            cursor.execute(""" 
                SELECT id, name, date, time, details FROM events 
                WHERE user_id = %s 
                ORDER BY date, time; 
            """, (user_id,)) 
            
            return cursor.fetchall()

    def update_event_by_id(self, event_id: int, user_id: int, new_name: str, new_date: date, new_time: time) -> None:
        """Обновляет все поля конкретной заметки по её уникальному id СУБД."""
        with self.conn.cursor() as cursor:
            cursor.execute("""
                UPDATE events 
                SET name = %s, date = %s, time = %s
                WHERE id = %s AND user_id = %s;
            """, (new_name, new_date, new_time, event_id, user_id))
            
            self.conn.commit()
            logging.info(f"Запись СУБД с ID {event_id} успешно обновлена пользователем {user_id}!")

    def delete_event(self, user_id: int, event_name: str) -> None:
        """Метод для УДАЛЕНИЯ строки таблицы events по имени события и ID пользователя."""
        with self.conn.cursor() as cursor:
      
            cursor.execute("""
                DELETE FROM events 
                WHERE name = %s AND user_id = %s;
            """, (event_name, user_id))
            
            self.conn.commit()
            logging.info(f"Событие '{event_name}' успешно удалено для {user_id}!")
