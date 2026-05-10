import httpx
from src.core.config import settings
from src.core.exceptions import NetworkError


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
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=5.0)
                
                if response.status_code in (401, 403):
                    raise ValueError("Invalid or expired CTFd token")
                    
                response.raise_for_status()
                return response.json().get("data", {})
        except httpx.RequestError as e:
            raise NetworkError("CTFd service is currently unavailable")