import pytest
import socket
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from src.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture(autouse=True)
def reset_singletons():
    import src.db.json_storage as js
    js._storage_data = None
    yield
    js._storage_data = None

@pytest.fixture
def mock_dns_success(mocker):
    mock_loop = mocker.Mock()
    mock_getaddrinfo = AsyncMock()
    mock_getaddrinfo.return_value = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('10.0.0.1', 0))]
    mock_loop.getaddrinfo = mock_getaddrinfo
    mocker.patch('src.core.security.asyncio.get_running_loop', return_value=mock_loop)
    return mock_getaddrinfo

@pytest.fixture
def mock_dns_error(mocker):
    mock_loop = mocker.Mock()
    mock_getaddrinfo = AsyncMock(side_effect=socket.gaierror)
    mock_loop.getaddrinfo = mock_getaddrinfo
    mocker.patch('src.core.security.asyncio.get_running_loop', return_value=mock_loop)
    return mock_getaddrinfo
