import time
import logging
from fastapi import FastAPI, Request
from src.core.config import settings
from src.api import routes
from src.core.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    docs_url=None,
    redoc_url=None
)

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

app.include_router(routes.router)

@app.get("/health", tags=['System'])
async def health_check() -> dict[str, str]:
    """Базовый Health-check."""
    return {"status": "ok"}