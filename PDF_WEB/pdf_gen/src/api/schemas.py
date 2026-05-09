from typing import List, Optional
from pydantic import BaseModel, Field

class TaskResult(BaseModel):
    """Схема отдельного решенного задания участника."""
    title: str = Field(..., description="Название задания")
    score: int = Field(..., description="Количество очков за задание")
    attempts: int = Field(..., description="Количество попыток сдачи")
    comment: Optional[str] = Field(None, description="Комментарий пользователя")

class CTFdReportData(BaseModel):
    """Схема полного отчета по игроку."""
    username: str = Field(..., description="Никнейм игрока")
    team: str = Field(..., description="Название команды")
    score: int = Field(..., description="Общий счет игрока")
    tasks: List[TaskResult] = Field(..., description="Список решенных тасков")

class GenerateResponse(BaseModel):
    pdf_base64: str = Field(..., description="Сгенерированный и подписанный PDF в Base64")