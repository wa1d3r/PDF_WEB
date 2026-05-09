from fastapi import FastAPI
from pdf_gen.src.core.config import settings
from pdf_gen.src.api import generate

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(generate.router)

@app.get('/health', tags=['System'], summary='Проверка статуса сервиса.')
async def health_check() -> dict[str, str]:
    """Базовый Health-check
    
    Returns:
        dict[str, str]: Статус работоспособности сервера
    """
    return {'status': 'ok'}