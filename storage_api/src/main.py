from fastapi import FastAPI
from src.api import public, internal
from src.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(public.router)
app.include_router(internal.router)

@app.get(
    '/health',
    tags=['System'],
    summary='Проверка статуса сервиса'
)
async def health_check() -> dict[str, str]:
    """Базовый health-check

    Returns:
        dict[str, str]: Статус работоспособности сервиса.
    """
    return {'status': 'ok'}
