from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Класс настроек сервиса PDF Gen.
    """
    PROJECT_NAME: str = 'PDF Generator Node'
    STORAGE_API_URL: str = 'http://storage'
    SIGNER_API_URL: str = 'http://signer'
    STAMP_TEXT: str = 'stamp_text'
    STAMP_IMG: str = 'stamp'

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

settings = Settings()