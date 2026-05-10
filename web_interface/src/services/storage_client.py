import httpx
from fastapi import HTTPException
from src.core.config import settings

class StorageClient:
    """Получение статической разметки и шаблонов из хранилища
    """

    async def get_html_template(self, template_name: str) -> str:
        ...
