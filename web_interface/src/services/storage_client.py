import httpx
import base64
from src.core.exceptions import NetworkError
from src.core.config import settings

class StorageClient:
    """Получение статической разметки и шаблонов из хранилища
    """

    async def get_html_template(self, template_name: str) -> str:
        """Скичивает публичный шаблон

        Args:
            template_name (str): Имя шаблона

        Raises:
            ValueError: Пустой шаблон
            NetworkError: Ошибка на стороне хранилдища или шаблон не найден
            RuntimeError: Ошибка в процессе декодирования шаблона

        Returns:
            str: Декодированная строка шаблона
        """
        url = f'{settings.STORAGE_API_URL}/public/assets/{template_name}'

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5.0)
                response.raise_for_status()

                b64_data = response.json().get('data', '')
                if not b64_data:
                    raise ValueError('Empty template')
                
                return base64.b64decode(b64_data).decode('utf-8')
            
        except httpx.HTTPError as e:
            raise NetworkError('UI assets unavailable')

        except Exception as e:
            raise RuntimeError('UI assets corrupted')
