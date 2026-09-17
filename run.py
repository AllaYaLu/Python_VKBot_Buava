import asyncio
import logging

# Импортируем настройки и класс приложения
from settings.config import AppSettings
# 1. Импортируем класс Application из файла app.main
from app.main import Application

def main():
    # Настраиваем вывод логов в консоль
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s]: %(message)s")
    
    # Загружаем настройки из Pydantic
    settings = AppSettings()
    
    # 2. Создаем объект бота
    app = Application(app_settings=settings)
    
    # 3. Запускаем асинхронную функцию run() нашего бота.
    asyncio.run(app.run())

if __name__ == "__main__":
    main()
