from typing import Annotated
from fastapi import Request, HTTPException, Depends
from fastapi.security import APIKeyHeader
from src.core.security import NetworkAccessControl
from src.core.config import settings

nac = NetworkAccessControl(
    master_secret=settings.MASTER_SECRET,
    allowed_domains=settings.ALLOWED_DOMAINS
)

service_token_shame = APIKeyHeader(
    name='X-Servive-Token',
    description='Токен доступа к сервису',
    auto_error=False
)

async def verify_service_access(
        request: Request,
        x_service_token: Annotated[
            str,
            Depends(service_token_shame)
        ]
) -> str:
    """Зависимость для защиты приватных эндпоинтов.

    Args:
        request (Request): Объект запроса FastAPI.
        x_service_token (str): Токен, переданный в заголовке X-Service-Token.
    
    Raises:
        HTTPException: Ошибка 401, если токен не прошел валидацию

    Returns:
        str: Валидированный токен сервиса
    """
    client_ip = request.client.host if request.client else 'unknown'

    if not nac.verify_access(x_service_token, client_ip):
        raise HTTPException(
            status_code=401,
            detail='Unauthorized. Invalid token.'
        )

    return x_service_token
