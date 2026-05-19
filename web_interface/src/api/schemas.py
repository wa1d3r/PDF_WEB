from pydantic import BaseModel, Field
from typing import List, Optional

class TokenRequest(BaseModel):
    """Модель запроса токена игрока
    """
    token: str = Field(..., description='Токен участника CTFd')

class TaskData(BaseModel):
    title: str
    score: int
    attempts: int
    comment: Optional[str] = None

class ManualReportRequest(BaseModel):
    username: str
    team: str
    score: int
    tasks: List[TaskData]
