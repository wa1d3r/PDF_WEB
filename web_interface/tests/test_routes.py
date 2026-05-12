import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport

from src.main import app
from src.services.storage_client import StorageClient
from src.services.ctfd_client import CTFdClient
from src.services.pdf_client import PDFGeneratorClient

@pytest.fixture
def mock_storage(): return AsyncMock(spec=StorageClient)

@pytest.fixture
def mock_ctfd(): return AsyncMock(spec=CTFdClient)

@pytest.fixture
def mock_pdf(): return AsyncMock(spec=PDFGeneratorClient)

@pytest.fixture
async def client(mock_storage, mock_ctfd, mock_pdf):
    app.dependency_overrides[StorageClient] = lambda: mock_storage
    app.dependency_overrides[CTFdClient] = lambda: mock_ctfd
    app.dependency_overrides[PDFGeneratorClient] = lambda: mock_pdf
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
        
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

@pytest.mark.asyncio
async def test_index_page(client, mock_storage):
    mock_storage.get_template.return_value = "<html>Login</html>"
    
    response = await client.get("/")
    assert response.status_code == 200
    assert "<html>Login</html>" in response.text
    mock_storage.get_template.assert_called_once_with("web_index.html")

@pytest.mark.asyncio
async def test_preview_report_success(client, mock_storage, mock_ctfd):
    mock_ctfd.fetch_user_data.return_value = {"username": "Admin"}
    mock_storage.get_template.return_value = "<h1>User: {{ data.username }}</h1>"
    
    response = await client.post("/api/preview", json={"token": "test_token"})
    
    assert response.status_code == 200
    assert "<h1>User: Admin</h1>" in response.text

@pytest.mark.asyncio
async def test_preview_report_auth_error(client, mock_ctfd):
    mock_ctfd.fetch_user_data.side_effect = ValueError("Invalid token")
    
    response = await client.post("/api/preview", json={"token": "bad_token"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"

@pytest.mark.asyncio
async def test_export_pdf_success(client, mock_ctfd, mock_pdf):
    mock_ctfd.fetch_user_data.return_value = {"username": "Admin"}
    mock_pdf.generate_pdf.return_value = b"%PDF-1.4 Fake Content"
    
    response = await client.post("/api/export", json={"token": "test_token"})
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == "attachment; filename=report.pdf"
    assert response.content == b"%PDF-1.4 Fake Content"

@pytest.mark.asyncio
async def test_export_pdf_generator_error(client, mock_ctfd, mock_pdf):
    mock_ctfd.fetch_user_data.return_value = {"username": "Admin"}
    mock_pdf.generate_pdf.side_effect = RuntimeError("RCE Output / Syntax Error")
    
    response = await client.post("/api/export", json={"token": "test_token"})
    
    assert response.status_code == 500
    assert response.json()["detail"] == "RCE Output / Syntax Error"

@pytest.mark.asyncio
async def test_export_pdf_auth_error(client, mock_ctfd):
    mock_ctfd.fetch_user_data.side_effect = ValueError("Invalid token")
    
    response = await client.post("/api/export", json={"token": "bad_token"})
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid token"

@pytest.mark.asyncio
async def test_preview_report_server_error(client, mock_storage, mock_ctfd):
    mock_ctfd.fetch_user_data.return_value = {"username": "Admin"}
    mock_storage.get_template.side_effect = Exception("Storage connection dropped")
    
    response = await client.post("/api/preview", json={"token": "valid_token"})
    
    assert response.status_code == 500
    assert response.json()["detail"] == "Storage connection dropped"