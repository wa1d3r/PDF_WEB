from pydantic import BaseModel, Field

class TokenRequest(BaseModel):
    """Модель запроса токена игрока
    """
    token: str = Field(..., description='Токен участника CTFd')