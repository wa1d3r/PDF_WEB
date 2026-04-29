import hmac
import hashlib
import socket

class NetworkAccessControl:
    """Класс управления доступом на основе сетевых адресов и криптографических токенов.

    Обеспечивает генерацию токенов доступа и их последующую проверку, включающую 
    валидацию подписи и сверку IP клиента с DNS записью домена.
    """
    def __init__(self, master_secret: str, allowed_domains: list[str]):
        """Инициализация системы контроля доступа.

        Args:
            master_secret (str): Ключ, используемый для генерации подписи.
            allowed_domains (list[str]): Список доменов, которым разрешен доступ к системе.
        """
        self._secret = master_secret.encode('utf-8')
        self._allowed_domains: set[str] = set(allowed_domains)
    
    def generate_token(self, domain: str) -> str:
        """Генерирует криптографический токен, привязанный к указанному домену.

        Args:
            domain (str): Имя домена, для которого выпускается токен.
        
        Raises:
            ValueError: Если привязанный домен отсутствует в списке разрешенных
        
        Returns:
            str: Токен в формате "<домен>.<подпись>"
        """
        if domain not in self._allowed_domains:
            raise ValueError('Domain {domain} is not allowed')
        
        signature = self._sign_payload(domain)
        return f"{domain}.{signature}"
    
    def verify_access(self, token: str, client_ip: str) -> bool:
        """Валидирует токен
        
        Проверяет наличие домена в списке разрешенных, криптографически проверяет
        подпись, проверяет соответствие фактического IP клиента по записям DNS
        
        Args:
            token (str): Токен, переданный клиентом
            client_ip (str): Фактический IP клиента
        
        Returns:
            bool: True, если токен валиден, иначе False.
        """
        if not token or '.' not in token:
            return False
        
        claimbed_domain, signature = token.split('.', 1)

        if claimbed_domain not in self._allowed_domains:
            return False
        
        expected_signature = self._sign_payload(claimbed_domain)
        if not hmac.compare_digest(expected_signature, signature):
            return False
        
        try:
            expected_ip = socket.gethostbyname(claimbed_domain)
            if expected_ip != client_ip:
                return False
        except socket.gaierror:
            return False
        
        return True
    
    def _sign_payload(self, payload: str) -> str:
        """Генерирует HMAC-SHA256 подпись для данных
        
        Args:
            payload (str): Данные, которые требуется подписать.
        
        Returns:
            str: Шестнадцатиричная строка, представляющая вычисленную подпись."""
        return hmac.new(self._secret, payload.encode('utf-8'), hashlib.sha256).hexdigest()
