import logging
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Path
from src.db.json_storage import get_storage
from src.api.deps import verify_service_access
from src.api.schemas import DataResponse

logger = logging.getLogger(__name__)

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
    secret_key: Annotated[str, Path(description='идентификатор запрашиваемого секрета', examples=['flag'])],
    storage: Annotated[dict, Depends(get_storage)]
) -> DataResponse:
    data = storage.get('internal', {}).get(secret_key)

    if not data:
        logger.warning(f"Internal secret not found: {secret_key}")
        raise HTTPException(status_code=404, detail='secret not found')
    
    return DataResponse(data=data)
