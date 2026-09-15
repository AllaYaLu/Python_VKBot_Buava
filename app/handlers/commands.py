import vk_api
import random
import logging
from datetime import date, time
from app.calendar import Calendar
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from datetime import date, time, timedelta
import json  

async def add_calendar_event_handler( 
    vk, user_id: int, date_str: str, time_str: str, text: str, calendar: Calendar 
) -> None:
    try:
        # Парсинг даты и времени (это у тебя уже написано)
        event_date = date.fromisoformat(date_str)
        event_time = time.fromisoformat(time_str)
        
        # Так как пользователь пишет: событие 2026-09-14 15:00 Купить кофе
        # Текст "Купить кофе" мы запишем как имя события, 
        # а детали (event_details) пока сделаем пустой строкой или продублируем текст
        event_name = text
        event_details = f"Заметка создана через ВК бота." 

        # ИСПРАВЛЕННЫЙ ВЫЗОВ: передаем все 5 обязательных параметров!
        calendar.create_event(
            user_id=user_id,
            event_name=event_name,
            event_date=event_date,
            event_time=event_time,
            event_details=event_details
        )

        vk.messages.send(
            user_id=user_id,
            message=f"📅 Событие '{event_name}' успешно сохранено в БД на {event_date} в {event_time}!",
            random_id=random.randint(1, 2**31 - 1)
        )
    except ValueError:
        vk.messages.send(
            user_id=user_id,
            message="❌ Ошибка! Формат: событие ГГГГ-ММ-ДД ЧЧ:ММ Текст (например: событие 2026-09-14 15:00 Кофе)",
            random_id=random.randint(1, 2**31 - 1)
        )


# (Все предыдущие импорты и хэндлеры остаются без изменений вверху!)

async def register_user_handler(vk, user_id: int, calendar: Calendar) -> None:
    """
    Обработчик для команды 'регистрация'.
    Регистрирует пользователя в базе данных и отправляет красивый ответ.
    """
    try:
        # 1. Вызови метод register_user у объекта calendar.
        # Передай туда текущий user_id и сохрани результат (True или False) в переменную is_new
        is_new = calendar.register_user(user_id=user_id)
        
        main_menu = get_main_keyboard()
        
        # Формируем красивый текст ответа в зависимости от того, новый это пользователь или нет
        if is_new:
            reply_message = (
                "🎉 Вы успешно зарегистрировались в Боте-Календаре!\n\n"
                "Теперь вам доступны все функции многопользовательского режима. "
                "Вы можете создавать свои личные события и управлять ими!"
            )
        else:
            reply_message = "ℹ️ Вы уже зарегистрированы в системе! Ваш личный календарь полностью готов к работе."
            
        # 2. Отправляем ответ пользователю в ВК.
        # Впиши правильные параметры в метод send: user_id, message и random_id
        vk.messages.send(
            user_id=user_id,
            message=reply_message,
            keyboard=main_menu,
            random_id=random.randint(1, 2**31 - 1)
        )
        
        logging.info(f"Обработана регистрация для пользователя {user_id}")
        
    except Exception as e:
        logging.error(f"Ошибка в обработчике регистрации: {e}")
        vk.messages.send(
            user_id=user_id,
            message="❌ Произошла ошибка при регистрации. Пожалуйста, попробуйте позже.",
            random_id=random.randint(1, 2**31 - 1)
        )


async def edit_calendar_event_handler(
    vk, user_id: int, payload: str, calendar: Calendar
) -> None:
    """Обработчик для изменения события с защитой от ошибок парсинга."""
    try:
        # 1. Разделяем строку по вертикальной черте
        parts = payload.split("|")
        
        # Проверяем, что пользователь передал хотя бы имя события
        if not parts or not parts[0].strip():
            raise ValueError("Имя события не может быть пустым")
            
        event_name = parts[0].strip()
        new_date = None
        new_description = None
        
        # 2. Если есть вторая часть, аккуратно извлекаем дату
        if len(parts) > 1 and parts[1].strip():
            new_date = date.fromisoformat(parts[1].strip())
            
        # 3. Если есть третья часть, извлекаем описание
        if len(parts) > 2 and parts[2].strip():
            new_description = parts[2].strip()
            
        # Вызываем метод класса базы данных
        calendar.edit_event(
            user_id=user_id,
            event_name=event_name,
            new_date=new_date,
            new_description=new_description
        )
        
        vk.messages.send(
            user_id=user_id,
            message=f"✅ Событие '{event_name}' успешно обновлено!",
            random_id=random.randint(1, 2**31 - 1)
        )
    except Exception as e:
        # Важно! Этот лог выведет настоящую причину падения в терминал VS Code,
        # чтобы мы не гадали, почему сработал блок except
        logging.error(f" [КРИТИЧЕСКАЯ ОШИБКА ПАРСИНГА ИЗМЕНЕНИЯ]: {e}")
        
        vk.messages.send(
            user_id=user_id,
            message="❌ Ошибка синтаксиса! Шаблон: изменить Название | ГГГГ-ММ-ДД | Описание",
            random_id=random.randint(1, 2**31 - 1)
        )


async def delete_calendar_event_handler(
    vk, user_id: int, event_name: str, calendar: Calendar
) -> None:
    """Обработчик для удаления события."""
    try:
        # Очищаем имя события от случайных пробелов по краям
        clean_name = event_name.strip()
        
        if not clean_name:
            raise ValueError("Имя события для удаления не может быть пустым")
        
        # Передаем параметры строго по именам, как написано в твоем классе Calendar
        calendar.delete_event(user_id=user_id, event_name=clean_name)
        
        vk.messages.send(
            user_id=user_id,
            message=f"🗑️ Событие '{clean_name}' успешно удалено из вашего календаря!",
            random_id=random.randint(1, 2**31 - 1)
        )
    except Exception as e:
        # Теперь, если что-то сломается, в терминале VS Code ОБЯЗАТЕЛЬНО появится эта строчка
        logging.error(f"❌ [ОШИБКА В ХЭНДЛЕРЕ УДАЛЕНИЯ]: {e}")
        
        vk.messages.send(
            user_id=user_id,
            message="❌ Не удалось удалить событие.",
            random_id=random.randint(1, 2**31 - 1)
        )


def get_main_keyboard() -> str:
    """Генерирует главную клавиатуру бота."""
    # Параметр one_time=False означает, что клавиатура не скроется после одного нажатия
    keyboard = VkKeyboard(one_time=False)
    
    # 1. Первая строчка кнопок — Регистрация (зеленая)
    keyboard.add_button("Регистрация", color=VkKeyboardColor.POSITIVE)
    
    # Переходим на новую строку клавиатуры
    keyboard.add_line()
    
    # 2. Вторая строчка — Создать (синяя) и Показать все (белая)
    keyboard.add_button("Создать заметку", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("Показать все заметки", color=VkKeyboardColor.SECONDARY)
    
    keyboard.add_line()
    
    # 3. Третья строчка — Изменить (белая) и Удалить (красная)
    keyboard.add_button("Изменить заметку", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("Удалить заметку", color=VkKeyboardColor.NEGATIVE)
    
    # Метод get_keyboard() превращает объект клавиатуры в JSON-строку для ВК
    return keyboard.get_keyboard()


def get_date_keyboard() -> str:
    """Генерирует клавиатуру для быстрого выбора даты."""
    keyboard = VkKeyboard(one_time=False)
    
    # Расчитываем даты программно
    today_date = date.today()                  # Сегодня: 2026-09-15
    tomorrow_date = today_date + timedelta(days=1)  # Завтра: ???
    
    # 1. Кнопка "Сегодня". Оборачиваем словарь в json.dumps()
    keyboard.add_button(
        label=f"Сегодня ({today_date.strftime('%d.%m')})",
        color=VkKeyboardColor.PRIMARY,
        payload=json.dumps({"command": "create_event_date", "date": str(today_date)})
    )
    
    # 2. Кнопка "Завтра". Тоже добавляем json.dumps()
    keyboard.add_button(
        label=f"Завтра ({tomorrow_date.strftime('%d.%m')})",
        color=VkKeyboardColor.PRIMARY,
        payload=json.dumps({"command": "create_event_date", "date": str(tomorrow_date)})
    )
    keyboard.add_line()
    
    # 3. Кнопка ручного ввода и отмены
    keyboard.add_button("Ввести вручную", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("↩️ Отмена", color=VkKeyboardColor.NEGATIVE)
    
    return keyboard.get_keyboard()

async def start_create_event_handler(vk, user_id: int) -> None:
    """Запускает процесс создания заметки и предлагает выбрать дату."""
    date_menu = get_date_keyboard()
    
    vk.messages.send(
        user_id=user_id,
        message="📅 Шаг 1: Выберите дату проведения события с помощью кнопок или введите её вручную в формате ГГГГ-ММ-ДД:",
        keyboard=date_menu,
        random_id=random.randint(1, 2**31 - 1)
    )
