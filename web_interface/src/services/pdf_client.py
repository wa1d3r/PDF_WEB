import httpx
import base64
import logging
from src.core.exceptions import NetworkError, ServiceError
from src.core.config import settings

logger = logging.getLogger(__name__)

class PDFGeneratorClient:
    """ Проксирование запросов на генерацию отчета
    """

    async def generate_pdf(self, payload: dict) -> bytes:
        """Отправка данных пользователя в сервис генерации

        Args:
            payload (dict): Пользовательские данные

        Raises:
            ServiceError: Ошибк на стороне генератора
            NetworkError: Ошибка соединения с генератором
            RuntimeError: Ошибка при обработке ответа от генератора

        Returns:
            bytes: Бинарный PDF файл
        """
        url = f'{settings.PDF_GEN_API_URL}/api/v1/generate'
        logger.info(f"Proxying generation request to PDF Gen for user '{payload.get('username')}'...")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)

                if response.status_code != 200:
                    error_detail = response.json().get('detail', 'runtime error')
                    logger.warning(f"PDF Gen returned error (Possible SSTI execution): {error_detail}")
                    raise ServiceError(error_detail)
                
                b64_data = response.json().get('pdf_base64', '')
                logger.info("Successfully received signed PDF from generator.")
                return base64.b64decode(b64_data)
        
        except httpx.HTTPError as e:
            logger.error(f"Failed to connect to PDF Gen API: {e}")
            raise NetworkError(f'Generator connection failed: {str(e)}')

        except Exception as e:
            logger.error(f"Internal processing error: {e}")
            raise RuntimeError(f'runtime error: {str(e)}')
