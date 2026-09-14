import os
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseSettings):
    """
    Класс конфигурации для бота-календаря.
    """
    # Токен ВК (тип SecretStr)
    VK_API_KEY: SecretStr = SecretStr("secret")

    # Настройки для подключения к БД PostgreSQL (типы str и SecretStr)
    DB_HOST: str = "localhost"
    DB_NAME: str = "calendar_bot"
    DB_USER: str = "postgres"
    DB_PASSWORD: SecretStr = SecretStr("secret")

    # Настройка пути к файлу .env
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), "../.env")
    )
