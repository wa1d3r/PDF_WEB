import aiohttp
import pytest
import base64
from unittest.mock import AsyncMock, call, MagicMock
from httpx import AsyncClient, ASGITransport
from fastapi import Request, FastAPI

from src.main import app, lifespan
from src.services.fetcher import SignatureAssetFetcher
from src.services.crypto import PDFCryptoSigner
from src.core.config import settings
from src.core.exceptions import (
    SecurityError,
    InvalidPayloadError,
    PayloadTooLargeError,
    NetworkError
)
from src.api.sign import get_fetcher

@pytest.fixture
def mock_fetcher():
    return AsyncMock(spec=SignatureAssetFetcher)

@pytest.fixture
def mock_crypto():
    return AsyncMock(spec=PDFCryptoSigner)

@pytest.fixture
async def client(mock_fetcher, mock_crypto):
    app.dependency_overrides[get_fetcher] = lambda: mock_fetcher
    app.dependency_overrides[PDFCryptoSigner] = lambda: mock_crypto

    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as ac:
        yield ac
    
    app.dependency_overrides.clear()

@pytest.fixture
def valid_payload():
    return {
        "document_base64": base64.b64encode(b"PDF Content").decode("utf-8"),
        "text_url": "http://storage/text.txt",
        "img_url": "http://storage/image.png"
    }

@pytest.mark.asyncio
async def test_lifespan_manager(mocker):
    mock_app = FastAPI()
    
    mock_session_instance = AsyncMock(spec=aiohttp.ClientSession)
    mocker.patch("aiohttp.ClientSession", return_value=mock_session_instance)

    async with lifespan(mock_app):
        assert hasattr(mock_app.state, "http_session")
        assert mock_app.state.http_session is mock_session_instance
        
        mock_session_instance.close.assert_not_called()

    mock_session_instance.close.assert_awaited_once()

@pytest.mark.asyncio
async def test_get_fetcher_dependency():
    """Тестирует саму зависимость get_fetcher для 100% покрытия."""
    req = MagicMock(spec=Request)
    req.app.state.http_session = "dummy_session"
    fetcher_instance = await get_fetcher(req)
    assert fetcher_instance._session == "dummy_session"

@pytest.mark.asyncio
async def test_middleware_unknown_client(mocker):
    """Покрывает краевой случай логирования при отсутствии IP клиента."""
    mock_logger = mocker.patch("src.main.logger.info")
    scope = {
        "type": "http", 
        "method": "GET", 
        "path": "/health", 
        "headers": [], 
        "client": None,
        "query_string": b"",
        "server": ("127.0.0.1", 80)
    }
    
    async def receive(): return {"type": "http.request"}
    async def send(msg): pass
    
    await app(scope, receive, send)
    
    mock_logger.assert_called_once()
    assert "IP: unknown" in mock_logger.call_args[0][0]

@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}

@pytest.mark.asyncio
async def test_sign_success(client, mock_fetcher, mock_crypto, valid_payload):
    mock_fetcher.fetch.side_effect = [
        b"  Text \n",
        b"ImageBytes",
        b"P12_Bytes"
    ]
    mock_crypto.apply_signature.return_value = b"Signed_PDF_Result"

    response = await client.post("/api/v1/sign", json=valid_payload)

    assert response.status_code == 200
    expected_response_b64 = base64.b64encode(b"Signed_PDF_Result").decode("utf-8")
    assert response.json() == {"signed_document_base64": expected_response_b64}

    expected_fetch_calls = [
        call(valid_payload["text_url"]),
        call(valid_payload["img_url"]),
        call(settings.PRIVATE_KEY_URL, is_user_provided=False)
    ]
    mock_fetcher.fetch.assert_has_calls(expected_fetch_calls)
    assert mock_fetcher.fetch.call_count == 3

    mock_crypto.apply_signature.assert_called_once_with(
        document_bytes=b"PDF Content",
        pkcs12_bytes=b"P12_Bytes",
        password=settings.PRIVATE_KEY_PASSWORD,
        signature_text="Text",
        image_bytes=b"ImageBytes"
    )

@pytest.mark.asyncio
async def test_validation_error_invalid_urls(client):
    bad_payload = {
        "document_base64": "SGVsbG8=",
        "text_url": "bad_url",
        "img_url": "http://storage/image.png"
    }
    response = await client.post("/api/v1/sign", json=bad_payload)
    
    assert response.status_code == 422
    assert 'text_url' in response.text

@pytest.mark.asyncio
async def test_security_error_returns_403(client, mock_fetcher, valid_payload):
    mock_fetcher.fetch.side_effect = SecurityError("WAFException")
    response = await client.post("/api/v1/sign", json=valid_payload)
    assert response.status_code == 403
    assert response.json()["detail"] == "WAFException"

@pytest.mark.asyncio
@pytest.mark.parametrize('exception_class, exception_msg', [
    (InvalidPayloadError, 'Not a valid file format'),
    (PayloadTooLargeError, 'File exceeds size limits'),
    (ValueError, 'Base64 decode failed')
])
async def test_payload_errors_422(client, mock_fetcher, valid_payload, exception_class, exception_msg):
    mock_fetcher.fetch.side_effect = exception_class(exception_msg)
    response = await client.post('/api/v1/sign', json=valid_payload)
    assert response.status_code == 422
    assert response.json()['detail'] == exception_msg

@pytest.mark.asyncio
async def test_network_error_502(client, mock_fetcher, valid_payload):
    mock_fetcher.fetch.side_effect = NetworkError('Connection timeout')
    response = await client.post('/api/v1/sign', json=valid_payload)
    assert response.status_code == 502
    assert response.json()['detail'] == 'Connection timeout'

@pytest.mark.asyncio
async def test_crypto_value_error_returns_422(client, mock_fetcher, mock_crypto, valid_payload):
    mock_fetcher.fetch.return_value = b"OK"
    mock_crypto.apply_signature.side_effect = ValueError("Invalid PKCS#12 container")
    response = await client.post("/api/v1/sign", json=valid_payload)
    assert response.status_code == 422
    assert response.json()["detail"] == "Invalid PKCS#12 container"