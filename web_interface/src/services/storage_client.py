import httpx
from fastapi import HTTPException
from src.core.config import settings

class StorageClient:
    """Получение статической разметки и шаблонов из хранилища
    """

    async def get_html_template(self, template_name: str) -> str:
        url = f'{settings.STORAGE_API_URL}/public/assets/{template_name}'

        try:
            ...
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail='UI assets unavailable')
