import asyncio
import logging
from settings.config import AppSettings
from app.main import Application

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

async def main():
    config = AppSettings()
    app = Application(app_settings=config)
    try:
        await app.run()
    finally:

        await app.application_shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем.")

