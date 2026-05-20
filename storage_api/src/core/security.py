import hmac
import hashlib
import socket
import asyncio
import time
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class NetworkAccessControl:
    """
    Класс для управления доступом к внутренним микросервисам на основе 
    криптографически подписанных токенов и кэшированных DNS-запросов.
    """

    def __init__(self, master_secret: str, allowed_domains: list[str]) -> None:
        """
        Инициализирует систему контроля доступа.

        Args:
            master_secret (str): Системный мастер-пароль.
            allowed_domains (list[str]): Список строковых имен доменов,
                которым изначально предоставляется право запрашивать токены.
        """
        self._secret: bytes = master_secret.strip().encode('utf-8')
        self._allowed_domains: set[str] = set(allowed_domains)
        self._dns_cache: dict[str, Tuple[str, float]] = {}
        self._cache_ttl: float = 300.0 

    def _sign_payload(self, payload: str) -> str:
        """
        Генерирует криптографическую подпись для заданной полезной нагрузки 
        с использованием алгоритма HMAC на базе SHA-256.

        Args:
            payload (str): Строка, для которой требуется 
                сгенерировать подпись.

        Returns:
            str: Шестнадцатеричное строковое представление сгенерированного хэша.
        """
        return hmac.new(self._secret, payload.encode('utf-8'), hashlib.sha256).hexdigest()

    def generate_token(self, domain: str) -> str:
        """
        Генерирует подписанный токен доступа для указанного домена.

        Args:
            domain (str): Имя домена, для которого запрашивается токен.

        Raises:
            ValueError: Если переданный домен отсутствует во внутреннем списке 
                разрешенных доменов (`_allowed_domains`).

        Returns:
            str: Сформированный токен доступа в формате "домен.подпись".
        """
        if domain not in self._allowed_domains:
            raise ValueError(f"Domain '{domain}' is not allowed to generate tokens.")
        signature = self._sign_payload(domain)
        return f"{domain}.{signature}"

    async def _get_ip_async(self, domain: str) -> str:
        """
        Асинхронно разрешает доменное имя в IP-адрес.

        Args:
            domain (str): Доменное имя для разрешения.

        Raises:
            socket.gaierror: Если системный резолвер не смог найти IP-адрес 
                для указанного домена.

        Returns:
            str: Строковое представление IPv4-адреса, соответствующего домену.
        """
        now = time.time()
        
        if domain in self._dns_cache:
            ip, expire_at = self._dns_cache[domain]
            if now < expire_at:
                return ip
                
        loop = asyncio.get_running_loop()
        try:
            addr_info = await loop.getaddrinfo(
                host=domain, 
                port=None, 
                family=socket.AF_INET, 
                type=socket.SOCK_STREAM
            )
            ip = addr_info[0][4][0]
            
            self._dns_cache[domain] = (ip, now + self._cache_ttl)
            return ip
            
        except socket.gaierror as e:
            raise e

    async def verify_access(self, token: str, client_ip: str) -> bool:
        """
        Осуществляет комплексную асинхронную проверку прав доступа на основе 
        переданного токена и фактического сетевого адреса клиента.

        Args:
            token (str): Токен доступа.
            client_ip (str): Фактический IPv4-адрес клиента.

        Returns:
            bool: `True`, если токен подлинный. В противном 
            случае `False`.
        """
        if not token or '.' not in token:
            logger.warning(f"NAC blocked [IP: {client_ip}]: Malformed or empty token.")
            return False
        
        try:
            claimbed_domain, signature = token.rsplit('.', 1)
        except ValueError:
            logger.warning(f"NAC blocked [IP: {client_ip}]: Invalid token format.")
            return False

        if claimbed_domain not in self._allowed_domains:
            logger.warning(f"NAC blocked [IP: {client_ip}]: Domain '{claimbed_domain}' not in allowed list.")
            return False
        
        expected_signature = self._sign_payload(claimbed_domain)
        if not hmac.compare_digest(expected_signature, signature):
            logger.warning(f"NAC blocked [IP: {client_ip}]: Invalid cryptographic signature for domain '{claimbed_domain}'.")
            return False
        
        try:
            expected_ip = await self._get_ip_async(claimbed_domain)
            if expected_ip != client_ip:
                logger.warning(f"NAC blocked [IP: {client_ip}]: IP mismatch for domain '{claimbed_domain}'. Expected IP: {expected_ip}.")
                return False
        except socket.gaierror:
            logger.warning(f"NAC blocked [IP: {client_ip}]: DNS lookup failed for domain '{claimbed_domain}'.")
            return False
        
        logger.info(f"NAC granted [IP: {client_ip}]: Access verified for domain '{claimbed_domain}'.")
        return True
