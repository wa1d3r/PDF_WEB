import httpx
from src.core.config import settings

class PDFGeneratorClient:
    """ Проксирование запросов на генерацию отчета
    """

    async def generate_pdf(self, payload: dict) -> bytes:
        ...
