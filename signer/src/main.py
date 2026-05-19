import aiohttp
import time
import logging
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager

from src.api import sign
from src.core.config import settings
from src.core.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_session = aiohttp.ClientSession()
    yield
    await app.state.http_session.close()

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    client_ip = request.client.host if request.client else "unknown"
    
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    logger.info(
        f"{request.method} {request.url.path} | "
        f"IP: {client_ip} | "
        f"Status: {response.status_code} | "
        f"{process_time:.2f}ms"
    )
    return response

app.include_router(sign.router)

@app.get('/health', tags=['System'], summary='Проверка статуса сервиса')
async def health_check() -> dict[str, str]:
    """Базовый health-check

    Returns:
        dict[str, str]: Статус работоспособности сервера
    """
    return {'status': 'ok'}
