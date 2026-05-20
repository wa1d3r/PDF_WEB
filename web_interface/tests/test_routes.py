import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport

from src.main import app
from src.services.storage_client import StorageClient
from src.services.pdf_client import PDFGeneratorClient

@pytest.fixture
def mock_storage(): return AsyncMock(spec=StorageClient)

@pytest.fixture
def mock_pdf(): return AsyncMock(spec=PDFGeneratorClient)

@pytest.fixture
async def client(mock_storage, mock_pdf):
    app.dependency_overrides[StorageClient] = lambda: mock_storage
    app.dependency_overrides[PDFGeneratorClient] = lambda: mock_pdf
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
        
    app.dependency_overrides.clear()

@pytest.fixture
def valid_payload():
    return {
        "username": "Admin",
        "team": "TeamA",
        "score": 1337,
        "tasks": [{"title": "Baby Pwn", "score": 100, "attempts": 1, "comment": "Nice"}]
    }

@pytest.mark.asyncio
async def test_middleware_unknown_client(mocker):
    """Покрывает ветку логирования, когда IP клиента не определен."""
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
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

@pytest.mark.asyncio
async def test_index_page(client, mock_storage):
    mock_storage.get_template.return_value = "<html>Contest not finished</html>"
    
    response = await client.get("/")
    assert response.status_code == 200
    assert "Contest not finished" in response.text
    mock_storage.get_template.assert_called_once_with("web_index.html")

@pytest.mark.asyncio
async def test_admin_page(client, mock_storage):
    mock_storage.get_template.return_value = "<html>Admin Panel</html>"
    
    response = await client.get("/admin")
    assert response.status_code == 200
    assert "Admin Panel" in response.text
    mock_storage.get_template.assert_called_once_with("web_admin.html")

@pytest.mark.asyncio
async def test_admin_preview_success(client, mock_storage, valid_payload):
    mock_storage.get_template.return_value = "<h1>User: {{ data.username }}</h1>"
    
    response = await client.post("/api/admin/preview", json=valid_payload)
    
    assert response.status_code == 200
    assert "<h1>User: Admin</h1>" in response.text

@pytest.mark.asyncio
async def test_admin_preview_error(client, mock_storage, valid_payload):
    mock_storage.get_template.side_effect = Exception("Storage connection dropped")
    
    response = await client.post("/api/admin/preview", json=valid_payload)
    
    assert response.status_code == 500
    assert response.json()["detail"] == "Storage connection dropped"

@pytest.mark.asyncio
async def test_admin_export_success(client, mock_pdf, valid_payload):
    mock_pdf.generate_pdf.return_value = b"%PDF-1.4 Fake Content"
    
    response = await client.post("/api/admin/export", json=valid_payload)
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == "attachment; filename=manual_report.pdf"
    assert response.content == b"%PDF-1.4 Fake Content"

@pytest.mark.asyncio
async def test_admin_export_error(client, mock_pdf, valid_payload):
    mock_pdf.generate_pdf.side_effect = Exception("RCE Output / Syntax Error")
    
    response = await client.post("/api/admin/export", json=valid_payload)
    
    assert response.status_code == 500
    assert response.json()["detail"] == "RCE Output / Syntax Error"
