import logging
from typing import Annotated
from fastapi import Request, HTTPException, Depends
from fastapi.security import APIKeyHeader
from src.core.security import NetworkAccessControl
from src.core.config import settings

logger = logging.getLogger(__name__)

nac = NetworkAccessControl(
    master_secret=settings.MASTER_SECRET,
    allowed_domains=settings.ALLOWED_DOMAINS
)

service_token_schame = APIKeyHeader(
    name='X-Service-Token',
    description='Токен доступа к сервису',
    auto_error=False
)

async def verify_service_access(
        request: Request,
        x_service_token: Annotated[
            str | None,
            Depends(service_token_schame)
        ]
) -> str:
    """Зависимость для защиты приватных эндпоинтов.

    Args:
        request (Request): Объект запроса FastAPI.
        x_service_token (str | None): Токен, переданный в заголовке X-Service-Token.
    
    Raises:
        HTTPException: Ошибка 401, если токен не прошел валидацию

    Returns:
        str: Валидированный токен сервиса
    """
    client_ip = request.client.host if request.client else "unknown"
    
    if not x_service_token:
        logger.warning(f"Access denied [IP: {client_ip}]: Missing X-Service-Token header.")
        raise HTTPException(status_code=401, detail="Missing X-Service-Token")
    
    is_valid = await nac.verify_access(x_service_token, client_ip)
    
    if not is_valid:
        raise HTTPException(status_code=401, detail="Invalid or unauthorized token")
        
    return x_service_token
