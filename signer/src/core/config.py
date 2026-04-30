from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """_summary_

    Attributes:
        PROJECT_NAME (str): Название проекта.
        SIGNER_TOKEN (str): Токен для межсервисного взаимодействия со Storage API
    """
    PROJECT_NAME: str = "Signature API"
    SIGNER_TOKEN: str = "token"

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

settings = Settings()