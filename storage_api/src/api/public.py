from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Path
from src.db.json_storage import get_storage
from src.api.schemas import DataResponse

router = APIRouter(
    prefix='/public',
    tags=['Public assets']
)

@router.get(
    '/assets/{asset_name}',
    summary='Получить публичный ассет',
    description='Возвращает содержимое ассета с публичным доступом',
    response_model=DataResponse,
    responses={
        404: {'description': 'Ассет не найден в базе данных'}
    }
)
async def get_public_asset(
    asset_name: Annotated[str, Path(description='идентификатор запрашиваемого ассета')],
    storage: Annotated[dict, Depends(get_storage)]
) -> DataResponse:
    """Обработчик получения публичных статических данных.

    Args:
        storage (dict): Словарь ассетов.
        asset_name (str): Имя ассета.

    Raises:
        HTTPException: 404, если ключ не найден в словаре.

    Returns:
        DataResponse: Модель с данными асета.
    """
    data = storage.get('public', {}).get(asset_name)

    if not data:
        raise HTTPException(status_code=404, detail='asset not found')
    
    return DataResponse(data=data)
