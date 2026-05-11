import pytest
import json
from unittest.mock import patch, ANY, mock_open
from fastapi import Request, HTTPException
from httpx import AsyncClient, ASGITransport

import src.db.json_storage as json_storage
from src.main import app
from src.db.json_storage import get_storage, load_storage
from src.api.deps import verify_service_access

@pytest.fixture
def mock_storage_data():
    return {
        'public': {
            'index.html': 'PGh0bWw+VGVzdCBQVUJMSUM8L2h0bWw+'
        },
        'internal': {
            'secret.html': 'PGh0bWw+VGVzdCBTRUNSRVQ8L2h0bWw+'
        }
    }

@pytest.fixture
def override_get_storage(mock_storage_data):
    async def _override():
        return mock_storage_data
    
    app.dependency_overrides[get_storage] = _override
    yield mock_storage_data
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

@pytest.fixture(autouse=True)
def reset_storage_cache():
    json_storage._storage_data = None
    yield
    json_storage._storage_data = None

def test_load_storage_file_exists():
    fake_data = {
        "public": {"file.txt": "base64=="},
        "internal": {"flag": "secret"}
    }
    fake_json_string = json.dumps(fake_data)

    with patch("src.db.json_storage.Path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=fake_json_string)) as mocked_file:
            result = load_storage()
            
            assert result == fake_data
            mocked_file.assert_called_once()

def test_load_storage_file_not_found():
    with patch("src.db.json_storage.Path.exists", return_value=False):
        result = load_storage()
        
        assert result == {"public": {}, "internal": {}}

def test_load_storage_caching():
    fake_data = {"public": {}, "internal": {"cached": "yes"}}
    fake_json_string = json.dumps(fake_data)

    with patch("src.db.json_storage.Path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=fake_json_string)) as mocked_file:
            result1 = load_storage()
            
            result2 = load_storage()
            
            assert result1 == result2 == fake_data
            mocked_file.assert_called_once()

@pytest.mark.asyncio
async def test_get_storage_async_wrapper():
    with patch("src.db.json_storage.Path.exists", return_value=False):
        result = await get_storage()
        assert result == {"public": {}, "internal": {}}

@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}

@pytest.mark.asyncio
async def test_get_public_asset_success(client, override_get_storage):
    response = await client.get('/public/assets/index.html')
    assert response.status_code == 200
    assert response.json()['data'] == 'PGh0bWw+VGVzdCBQVUJMSUM8L2h0bWw+'

@pytest.mark.asyncio
async def test_get_public_asset_not_found(client, override_get_storage):
    response = await client.get('/public/assets/missing.html')
    assert response.status_code == 404
    assert response.json()['detail'] == 'asset not found'

@pytest.mark.asyncio
async def test_get_secret_success(client, override_get_storage, mock_nac):
    mock_nac.return_value = True

    response = await client.get(
        '/internal/secrets/secret.html',
        headers={'X-Service-Token': 'valid.valid'}
    )
    assert response.status_code == 200
    assert response.json()['data'] == 'PGh0bWw+VGVzdCBTRUNSRVQ8L2h0bWw+'

    mock_nac.assert_called_once_with('valid.valid', ANY)

@pytest.mark.asyncio
async def test_get_secret_missing_token(client, override_get_storage, mock_nac):
    response = await client.get('/internal/secrets/secret.html')
    assert response.status_code == 401
    assert 'Unauthorized' in response.json()['detail']
    mock_nac.assert_not_called()

@pytest.mark.asyncio
async def test_get_secret_invalid_token_validate(client, override_get_storage, mock_nac):
    mock_nac.return_value = False

    response = await client.get(
        '/internal/secrets/secret.html',
        headers={'X-Service-Token': 'bad.bad'}
    )

    assert response.status_code == 401
    assert 'Unauthorized' in response.json()['detail']

@pytest.mark.asyncio
async def test_get_secret_not_found(client, override_get_storage, mock_nac):
    mock_nac.return_value = True

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