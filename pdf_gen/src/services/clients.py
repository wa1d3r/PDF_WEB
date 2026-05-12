import httpx
import logging
import base64
from src.core.config import settings
from src.core.exceptions import NetworkError

logger = logging.getLogger(__name__)

class StorageClient:
    """Клиент для получения публичных ассетов из Storage API."""
    
    async def get_template(self, template_name: str) -> str:
        """Скачивает и декодирует шаблон из хранилища.

        Args:
            template_name (str): Имя файла шаблона в хранилище.

        Raises:
            NetworkError: Ошибка при обращении к хранилищу

        Returns:
            str: Декодированный код шаблона.
        """
        logger.info(f"Fetching template '{template_name}' from Storage API...")
        url = f"{settings.STORAGE_API_URL}/public/assets/{template_name}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5.0)
                response.raise_for_status()
                
                b64_data = response.json().get("data", "")
                decoded_bytes = base64.b64decode(b64_data)

                logger.info(f"Successfully fetched and decoded template '{template_name}'.")
                return decoded_bytes.decode('utf-8')
                
        except Exception as e:
            logger.error(f"Failed to fetch template from Storage API: {e}")
            raise NetworkError(f"Storage API error: {str(e)}")

class SignerClient:
    """Клиент для отправки сгенерированного PDF на подписание."""
    
    async def sign_pdf(self, pdf_base64: str) -> str:
        """Отправляет PDF документ в сервис Signer.

        Args:
            pdf_base64 (str): Исходный PDF документ в Base64.

        Raises:
            NetworkError: Ошибка при обращении к хранилищу    
        
        Returns:
            str: Подписанный PDF документ в Base64.
        """
        url = f"{settings.SIGNER_API_URL}/api/v1/sign"
        logger.info("Sending rendered PDF to Signer API for cryptographic signature...")
        
        payload = {
            "document_base64": pdf_base64,
            "text_url": f"{settings.STORAGE_API_URL}/public/assets/{settings.STAMP_TEXT}",
            "image_url": f"{settings.STORAGE_API_URL}/public/assets/{settings.STAMP_IMG}"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)
                response.raise_for_status()

                logger.info("Successfully received signed PDF from Signer API.")
                return response.json().get("signed_document_base64", "")
                
        except Exception as e:
            logger.error(f"Failed to sign PDF via Signer API: {e}")
            raise NetworkError(f"Signer API error: {str(e)}")
