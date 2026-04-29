import redis.asyncio as redis
from src.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL)

async def get_redis() -> redis.Redis:
    """Зависимость для получения БД

    Returns:
        redis.Redis: БД из глобального пула.
    """
    return redis_client