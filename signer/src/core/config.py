from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """_summary_

    Attributes:
        PROJECT_NAME (str): Название проекта.
        SIGNER_TOKEN (str): Токен для межсервисного взаимодействия со Storage API
        MAX_DOCUMENT_SIZE (int): Максимальный размер base64 кодированного документа
    """
    PROJECT_NAME: str = "Signature API"
    SIGNER_TOKEN: str = "token"
    MAX_DOCUMENT_SIZE: int = 50 * 1024

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

settings = Settings()
