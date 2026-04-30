import aiohttp
import base64
from typing import Any
from src.core.config import settings
from src.core.exceptions import (
    SecurityError,
    InvalidPayloadError,
    PayloadTooLargeError,
    NetworkError
)

class SignatureTextFetcher:
    """Класс для получения актуального текста для штампа подписи
    """
    def __init__(self):
        """Инициализация заголовками для внутренних запросов
        """
        self._headers = { 'X-Service-Token': settings.SIGNER_TOKEN }
        self._max_doc_size = self.MAX_DOCUMENT_SIZE
    
    async def fetch(self, url: str) -> str:
        """Оркестратор процесса скачивания и обработки текста.

        Args:
            url (str): URL адрес для загрузки текста.

        Raises:
            InvalidPayloadError: Вызывается при несоответствии формату ответа (ожидается JSON).
            NetworkError: Сетевая ошибка при скачивании даных.

        Returns:
            str: Декодированный текст
        """
        self._check_waf_rules(url)

        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url, timeout=5) as response:
                    response.raise_for_status()
                    
                    try:
                        resp_json = await response.json()
                    except Exception:
                        raise InvalidPayloadError("Invalid response format: Expected JSON")

                    text = self._decode_payload(resp_json)
                    self._check_size_limits(text)
                    
                    return text.strip()
                    
        except aiohttp.ClientError as e:
            raise NetworkError(f"HTTP Request failed: {str(e)}")

    def _check_waf_rules(self, url: str) -> None:
        """Проверяет URL на соответствие базовым правилам безопасности.

        Args:
            url (str): Запрашиваемый URL-адрес.

        Raises:
            SecurityBlockError: Если URL содержит запрещенные пути.
        """
        if "/internal/" in url:
            raise SecurityError("WAFException: Cannot fetch from /internal/ paths.")

    def _decode_payload(self, payload: dict[str, Any]) -> str:
        """Извлекает и декодирует Base64 данные из JSON ответа.

        Args:
            payload (dict): Десериализованный JSON ответ.

        Raises:
            InvalidPayloadError: Если отсутствуют нужные ключи или Base64 поврежден.

        Returns:
            str: Декодированная UTF-8 строка.
        """
        encoded_data = payload.get("data")
        if not encoded_data:
            raise InvalidPayloadError("Invalid response format: Missing 'data' field")
            
        try:
            decoded_bytes = base64.b64decode(encoded_data)
            return decoded_bytes.decode('utf-8')
        except Exception as e:
            raise InvalidPayloadError("Invalid base64 payload structure")

    def _check_size_limits(self, text: str) -> None:
        """Проверяет, не превышает ли текст установленные лимиты.

        Args:
            text (str): Расшифрованный текст подписи.

        Raises:
            PayloadTooLargeError: Если текст превышает MAX_PAYLOAD_SIZE.
        """
        if len(text) > self._max_doc_size:
            raise PayloadTooLargeError(
                f"PayloadTooLarge: Response exceeds {self._max_doc_size} bytes limit"
            )
