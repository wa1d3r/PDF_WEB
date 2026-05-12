from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Web Proxy"
    
    STORAGE_API_URL: str = "http://storage"
    PDF_GEN_API_URL: str = "http://pdf_gen"
    CTFD_API_URL: str = "http://ctfd"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()