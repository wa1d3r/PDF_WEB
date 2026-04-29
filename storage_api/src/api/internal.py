from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Path
from redis.asyncio import Redis
from src.db.redis import get_redis
from src.api.deps import verify_service_access
from src.api.schemas import DataResponse

router = APIRouter(
    prefix='/internal',
    tags=['Internal secrets'],
    dependencies=[Depends(verify_service_access)]
)

@router.get(
    '/secrets/{secret_key}',
    response_model=DataResponse,
    summary='Получить приватный ассет',
    responses={
        401: {'description': 'Отказ в доступе'},
        404: {'description': 'Секрет не найден'}
    },
)
async def get_secret(
    secret_key: Annotated[
        str, 
        Path(
            description='идентификатор запрашиваемого секрета',
            examples=['flag']
            )
        ],
    redis_client: Annotated[Redis, Depends(get_redis)]
) -> DataResponse:
    data = await redis_client.get(f'secret:{secret_key}')

    if not data:
        raise HTTPException(status_code=404, detail='secret not found')
    
    return DataResponse(data=data)
