import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models import Base  
from settings.config import AppSettings
from contextlib import asynccontextmanager

class Database:
    def __init__(self, app_settings: AppSettings):
        self.db_url = (
            f"postgresql+asyncpg://{app_settings.DB_USER}:{app_settings.DB_PASSWORD.get_secret_value()}"
            f"@{app_settings.DB_HOST}/{app_settings.DB_NAME}"
        )
        self.engine = create_async_engine(self.db_url, echo=False)
        self._async_session = async_sessionmaker(self.engine, expire_on_commit=False)
        logging.info("Движок SQLAlchemy инициализирован.")

    async def create_tables(self):
        """Создание таблиц через метод begin"""
        async with self.engine.begin() as conn:
            # metadata теперь содержит информацию о users и orders на 100%
            await conn.run_sync(Base.metadata.create_all)
        logging.info("Таблицы базы данных успешно проверены/созданы в PostgreSQL.")

    async def shutdown(self):
        """Закрытие соединений при выключении"""
        await self.engine.dispose()
        logging.info("Соединения с базой данных закрыты.")

    @asynccontextmanager
    async def session(self):
        """Контекстный менеджер для безопасной работы с сессиями"""
        async with self._async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                raise e
