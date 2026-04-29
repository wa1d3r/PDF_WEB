import pytest
import base64
from unittest.mock import patch, AsyncMock, ANY
from fastapi import Request, HTTPException
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.db.redis import get_redis
from src.api.deps import verify_service_access

@pytest.fixture
def mock_redis():
    return AsyncMock()

@pytest.fixture
def override_get_redis(mock_redis):
    async def _override():
        return mock_redis
    
    app.dependency_overrides[get_redis] = _override
    yield mock_redis
    app.dependency_overrides.clear()

@pytest.fixture
def mock_nac():
    with patch('src.api.deps.nac.verify_access') as mock:
        yield mock

@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url='http://testserver'
    ) as ac:
        yield ac

@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}

@pytest.mark.asyncio
async def test_get_public_asset_success(client, override_get_redis):
    raw_bytes = b'<html>Test PUBLIC</html>'
    expected_base64 = base64.b64encode(raw_bytes).decode('utf-8')
    override_get_redis.get.return_value = raw_bytes

    response = await client.get('/public/assets/index.html')
    assert response.status_code == 200
    assert response.json()['data'] == expected_base64
    override_get_redis.get.assert_called_once_with('asset:index.html')

@pytest.mark.asyncio
async def test_get_public_asset_not_found(client, override_get_redis):
    override_get_redis.get.return_value = None

    response = await client.get('/public/assets/missing.html')
    assert response.status_code == 404
    assert response.json()['detail'] == 'asset not found'

@pytest.mark.asyncio
async def test_get_secret_success(client, override_get_redis, mock_nac):
    mock_nac.return_value = True
    raw_bytes = b'<html>Test SECRET</html>'
    expected_base64 = base64.b64encode(raw_bytes).decode('utf-8')
    override_get_redis.get.return_value = raw_bytes

    response = await client.get(
        '/internal/secrets/secret.html',
        headers={'X-Service-Token': 'valid.valid'}
    )
    assert response.status_code == 200
    assert response.json()['data'] == expected_base64

    mock_nac.assert_called_once_with('valid.valid', ANY)
    override_get_redis.get.assert_called_once_with('secret:secret.html')

@pytest.mark.asyncio
async def test_get_secret_missing_token(client, override_get_redis, mock_nac):
    response = await client.get('/internal/secrets/secret.html')
    assert response.status_code == 401
    assert 'Unauthorized' in response.json()['detail']
    mock_nac.assert_not_called()
    override_get_redis.get.assert_not_called()

@pytest.mark.asyncio
async def test_get_secret_invalid_token_validate(client, override_get_redis, mock_nac):
    mock_nac.return_value = False

    response = await client.get(
        '/internal/secrets/secret.html',
        headers={'X-Service-Token': 'bad.bad'}
    )

    assert response.status_code == 401
    assert 'Unauthorized' in response.json()['detail']
    override_get_redis.get.assert_not_called()

@pytest.mark.asyncio
async def test_get_secret_not_found(client, override_get_redis, mock_nac):
    mock_nac.return_value = True
    override_get_redis.get.return_value = None

    response = await client.get(
        '/internal/secrets/missing.html',
        headers={'X-Service-Token': 'valid.valid'}
    )

    assert response.status_code == 404
    assert response.json()['detail'] == 'secret not found'

@pytest.mark.asyncio
async def test_verify_service_access_no_client_ip(mock_nac):
    mock_nac.return_value = False
    scope = {
        'type': 'http',
        'method': 'GET',
        'url': 'http://testserver',
        'headers': [],
        'client': None
    }
    request = Request(scope)

    with pytest.raises(HTTPException) as e:
        await verify_service_access(request, x_service_token='some_token')
    
    assert e.value.status_code == 401
    mock_nac.assert_called_once_with('some_token', 'unknown')
