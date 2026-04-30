class FetcherError(Exception):
    """Базовый класс ошибок скачивания контента
    """
    pass

class SecurityError(FetcherError):
    """Ошибка при срабатывании WAF"""
    pass

class InvalidPayloadError(FetcherError):
    """Выбрасывается при несоответствии ожидаемому формату"""
    pass

class PayloadTooLargeError(FetcherError):
    """Выбрасывается при превышении лимита скачиваемых данных"""
    pass

class NetworkError(FetcherError):
    """Выбрасывется при сетевых ошибках"""
    pass