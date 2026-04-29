from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Класс настроек приложения

    Attributes:
        PROJECT_NAME (str): Название проекта.
        REDIS_URL (str): Адрес сервера Redis.
        MASTER_SECRET (str): Ключ для генерации и валидации HMAC токенов.
        ALLOWED_DOMAINS (list[str]): Список доменов, имеющих доступ к закрытому API
    """
    PROJECT_NAME: str = "Storage API"
    REDIS_URL: str = "redis://redis:6379/0"
    MASTER_SECRET: str = "secret-key"
    ALLOWED_DOMAINS: list[str] = []

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

settings = Settings()
