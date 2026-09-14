import asyncio
import logging

# Импортируем настройки и класс нашего приложения
from settings.config import AppSettings
# 1. Импортируй класс Application из файла app.main
from app.main import Application

def main():
    # Настраиваем вывод логов в консоль
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s]: %(message)s")
    
    # Загружаем настройки из Pydantic
    settings = AppSettings()
    
    # 2. Создай объект бота (экземпляр класса Application) и передай туда наш settings
    app = Application(app_settings=settings)
    
    # 3. Запускаем асинхронную функцию run() нашего бота.
    # Передай корутину app.run() внутрь asyncio.run()
    asyncio.run(app.run())

if __name__ == "__main__":
    main()
