from fastapi import FastAPI
from src.core.config import settings
from src.api import routes

app = FastAPI(
    title=settings.PROJECT_NAME,
    docs_url=None,
    redoc_url=None
)

app.include_router(routes.router)

@app.get("/health", tags=['System'])
async def health_check() -> dict[str, str]:
    """Базовый Health-check."""
    return {"status": "ok"}