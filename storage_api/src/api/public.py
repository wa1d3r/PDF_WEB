from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Path
from redis.asyncio import Redis
from src.db.redis import get_redis
from src.api.schemas import DataResponse

router = APIRouter(
    prefix='/public',
    tags=['Public assets']
)

@router.get(
    '/asset/{asset_name}',
    summary='Получить публичный ассет',
    description='Возвращает содержимое ассета с публичным доступом',
    response_model=DataResponse,
    responses={
        404: {'description': 'Ассет не найден в базе данных'}
    }
)
async def get_public_asset(
    asset_name: Annotated[str, Path(description='идентификатор запрашиваемого ассета')],
    redis_client: Annotated[Redis, Depends(get_redis)]
) -> DataResponse:
    """Обработчик получения публичных статических данных.

    Args:
        redis_client (Redis): Клиент базы данных.
        asset_name (str): Имя ассета.

    Raises:
        HTTPException: 404, если ключ не найден в Redis.

    Returns:
        DataResponse: Модель с данными асета.
    """
    data = await redis_client.get(f'asset:{asset_name}')

    if not data:
        raise HTTPException(status_code=404, detail='asset not found')
    
    return DataResponse(data=data)
