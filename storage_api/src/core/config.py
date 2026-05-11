from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Класс настроек приложения

    Attributes:
        PROJECT_NAME (str): Название проекта.
        STORAGE_FILE_PATH (str): Путь к JSON файлу с данными хранилища.
        MASTER_SECRET (str): Ключ для генерации и валидации HMAC токенов.
        ALLOWED_DOMAINS (list[str]): Список доменов, имеющих доступ к закрытому API
    """
    PROJECT_NAME: str = "Storage API"
    STORAGE_FILE_PATH: str = "data.json"
    MASTER_SECRET: str = "secret-key"
    ALLOWED_DOMAINS: list[str] = []

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

settings = Settings()
