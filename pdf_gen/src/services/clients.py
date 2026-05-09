import httpx
import base64
from pdf_gen.src.core.config import settings
from pdf_gen.src.core.exceptions import NetworkError

class StorageClient:
    """Клиент для получения публичных ассетов из Storage API."""
    
    async def get_template(self, template_name: str) -> str:
        """Скачивает и декодирует HTML-шаблон из хранилища.

        Args:
            template_name (str): Имя файла шаблона в хранилище.

        Raises:
            NetworkError: Ошибка при обращении к хранилищу

        Returns:
            str: Декодированный HTML код шаблона.
        """
        url = f"{settings.STORAGE_API_URL}/public/assets/{template_name}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5.0)
                response.raise_for_status()
                
                b64_data = response.json().get("data", "")
                decoded_bytes = base64.b64decode(b64_data)
                return decoded_bytes.decode('utf-8')
                
        except Exception as e:
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
        
        payload = {
            "document_base64": pdf_base64,
            "text_url": f"{settings.STORAGE_API_URL}/public/assets/{settings.STAMP_TEXT}",
            "image_url": f"{settings.STORAGE_API_URL}/public/assets/{settings.STAMP_IMG}"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)
                response.raise_for_status()
                return response.json().get("signed_document_base64", "")
                
        except Exception as e:
            raise NetworkError(f"Signer API error: {str(e)}")