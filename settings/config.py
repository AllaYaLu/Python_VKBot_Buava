import os
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseSettings):
    """
    Класс конфигурации для бота-кафе.
    Все значения автоматически подтягиваются из файла .env по именам переменных.
    """
    VK_API_KEY: SecretStr

    DB_HOST: str
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: SecretStr

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), "../.env")
    )

    ADMIN_INTERFACE_PORT: int
    ADMIN_SECRET_KEY: SecretStr
    ADMIN_LOGIN: SecretStr
    ADMIN_PASSWORD: SecretStr
