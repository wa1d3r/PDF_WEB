from fastapi import FastAPI
from src.core.config import settings
from src.api import sign

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(sign.router)

@app.get('/health', tags=['System'], summary='Проверка статуса сервиса')
async def health_check() -> dict[str, str]:
    """Базовый health-check

    Returns:
        dict[str, str]: Статус работоспособности сервера
    """
    return {'status': 'ok'}