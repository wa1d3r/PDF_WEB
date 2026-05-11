import aiohttp
import base64
import logging
import posixpath
import re
import urllib
from typing import Any
from src.core.config import settings
from src.core.exceptions import (
    SecurityError,
    InvalidPayloadError,
    PayloadTooLargeError,
    NetworkError
)

logger = logging.getLogger(__name__)

class SignatureAssetFetcher:
    """Класс для получения актуального ассета для штампа подписи
    """

    _INTERNAL_REGEX = re.compile(r'(?:^|/)internal(?:/|$)', re.IGNORECASE)

    def __init__(self):
        """Инициализация заголовками для внутренних запросов
        """
        self._secret_headers = { 'X-Service-Token': settings.SIGNER_TOKEN }
        self._max_doc_size = settings.MAX_DOCUMENT_SIZE
    
    async def fetch(self, url: str, is_user_provided: bool = True) -> bytes:
        """Оркестратор процесса скачивания и обработки ассета.

        Args:
            url (str): URL адрес для загрузки ассета.

        Raises:
            InvalidPayloadError: Вызывается при несоответствии формату ответа (ожидается JSON).
            NetworkError: Сетевая ошибка при скачивании даных.

        Returns:
            bytes: Декодированный ассет
        """
        if is_user_provided:
            self._check_waf_rules(url)

        logger.info(f"Fetching asset from URL: {url}")

        try:
            async with aiohttp.ClientSession(headers=self._secret_headers) as session:
                async with session.get(url, timeout=5) as response:
                    response.raise_for_status()
                    
                    try:
                        resp_json = await response.json()
                    except Exception:
                        logger.error(f"Fetch failed for {url}: Expected JSON response.")
                        raise InvalidPayloadError("Invalid response format: Expected JSON")

                    asset_bytes = self._decode_payload(resp_json)
                    self._check_size_limits(asset_bytes)
                    
                    logger.info(f"Successfully fetched and decoded {len(asset_bytes)} bytes from {url}")
                    return asset_bytes
                    
        except aiohttp.ClientError as e:
            logger.error(f"Network error while fetching {url}: {e}")
            raise NetworkError(f"HTTP Request failed: {str(e)}")

    def _check_waf_rules(self, url: str) -> None:
        """Проверяет URL на соответствие базовым правилам безопасности.

        Args:
            url (str): Запрашиваемый URL-адрес.

        Raises:
            SecurityBlockError: Если URL содержит запрещенные пути.
        """
        try:
            parsed = urllib.parse.urlparse(url)
        except Exception:
            logger.warning(f"WAF Blocked: Malformed URL structure: {url}")
            raise SecurityError("WAF: Malformed URL structure.")

        if parsed.scheme not in ("http", "https"):
            logger.warning(f"WAF Blocked: Invalid scheme '{parsed.scheme}' in {url}")
            raise SecurityError("WAF: Only HTTP/HTTPS schemes are allowed.")

        path = parsed.path
        decode_count = 0
        while '%' in path and decode_count < 3:
            new_path = urllib.parse.unquote(path)
            if new_path == path:
                break
            path = new_path
            decode_count += 1
            
        if decode_count >= 3:
            logger.warning(f"WAF Blocked: URL is over-encoded: {url}")
            raise SecurityError("WAF: URL is over-encoded.")

        normalized_path = posixpath.normpath(path.replace('\\', '/'))

        if not normalized_path.isascii():
            logger.warning(f"WAF Blocked: Non-ASCII characters detected: {url}")
            raise SecurityError("WAF: Non-ASCII characters are not allowed in URLs.")

        if ';' in normalized_path:
            logger.warning(f"WAF Blocked: Matrix parameters detected: {url}")
            raise SecurityError("WAF: Matrix parameters are not allowed.")

        if self._INTERNAL_REGEX.search(normalized_path):
            logger.warning(f"WAF Blocked: Attempt to access internal path: {url}")
            raise SecurityError("WAF: Cannot fetch from this path.")

    def _decode_payload(self, payload: dict[str, Any]) -> bytes:
        """Извлекает и декодирует Base64 данные из JSON ответа.

        Args:
            payload (dict): Десериализованный JSON ответ.

        Raises:
            InvalidPayloadError: Если отсутствуют нужные ключи или Base64 поврежден.

        Returns:
            bytes: Декодированный объект.
        """
        encoded_data = payload.get("data")
        if not encoded_data:
            logger.warning("Invalid response format: Missing 'data' field")
            raise InvalidPayloadError("Invalid response format: Missing 'data' field")
            
        try:
            return base64.b64decode(encoded_data)
        except Exception:
            logger.warning("Invalid base64 payload structure")
            raise InvalidPayloadError("Invalid base64 payload structure")

    def _check_size_limits(self, asset: bytes) -> None:
        """Проверяет, не превышает ли текст установленные лимиты.

        Args:
            asset (bytes): Расшифрованный текст подписи.

        Raises:
            PayloadTooLargeError: Если размер ассета превышает self._max_doc_size.
        """
        if len(asset) > self._max_doc_size:
            logger.warning(f"Fetch rejected: Asset size ({len(asset)} bytes) exceeds limit ({self._max_doc_size} bytes).")
            raise PayloadTooLargeError(
                f"PayloadTooLarge: Response exceeds {self._max_doc_size} bytes limit"
            )
