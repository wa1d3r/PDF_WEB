import httpx
import logging
from src.core.config import settings
from src.core.exceptions import NetworkError

logger = logging.getLogger(__name__)

class CTFdClient:
    """Отвечает за аутентификацию и сбор статистики игрока."""

    async def fetch_user_data(self, token: str) -> dict:
        """Запрашивает профиль пользователя из CTFd.

        Args:
            token (str): Токен пользователя.
        
        Raises:
            ValueError: При неверном токене или ошибке авторизации.
            NetworkError: При недоступности CTFd

        Returns:
            dict: Словарь со статистикой.
        """
        url = f"{settings.CTFD_API_URL}/api/v1/profile"
        headers = {"Authorization": f"Bearer {token}"}

        logger.info("Verifying user token with CTFd API...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=5.0)
                
                if response.status_code in (401, 403):
                    logger.warning("CTFd rejected token (Invalid or expired).")
                    raise ValueError("Invalid or expired CTFd token")
                    
                response.raise_for_status()
                data = response.json().get("data", {})
                logger.info(f"Successfully fetched profile for user: '{data.get('username', 'Unknown')}'")
                return data
            
        except httpx.RequestError as e:
            logger.error(f"CTFd API connection failed: {e}")
            raise NetworkError("CTFd service is currently unavailable")
