import pytest
import base64
import httpx
from unittest.mock import patch, MagicMock

from src.services.storage_client import StorageClient
from src.services.pdf_client import PDFGeneratorClient
from src.core.exceptions import NetworkError, ServiceError


@pytest.mark.asyncio
async def test_storage_client_success():
    client = StorageClient()
    template_html = "<h1>Test</h1>"
    b64_content = base64.b64encode(template_html.encode()).decode()
    
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"data": b64_content}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        result = await client.get_template("test.html") 
        assert result == template_html

@pytest.mark.asyncio
async def test_storage_client_empty_data():
    client = StorageClient()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"data": ""}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="UI assets corrupted"):
            await client.get_template("test.html")

@pytest.mark.asyncio
async def test_storage_client_network_error():
    client = StorageClient()
    with patch("httpx.AsyncClient.get", side_effect=httpx.RequestError("Timeout")):
        with pytest.raises(NetworkError, match="UI assets unavailable"):
            await client.get_template("test.html")


@pytest.mark.asyncio
async def test_pdf_client_success():
    client = PDFGeneratorClient()
    fake_pdf_bytes = b"PDF_CONTENT"
    b64_pdf = base64.b64encode(fake_pdf_bytes).decode()
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"pdf_base64": b64_pdf}

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        result = await client.generate_pdf({"username": "Admin"})
        assert result == fake_pdf_bytes

@pytest.mark.asyncio
async def test_pdf_client_service_error():
    client = PDFGeneratorClient()
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.json.return_value = {"detail": "Jinja2 Syntax Error"}

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="runtime error: Jinja2 Syntax Error"):
            await client.generate_pdf({"username": "Admin"})

@pytest.mark.asyncio
async def test_pdf_client_network_error():
    client = PDFGeneratorClient()
    with patch("httpx.AsyncClient.post", side_effect=httpx.HTTPError("Down")):
        with pytest.raises(NetworkError, match="Generator connection failed"):
            await client.generate_pdf({"username": "Admin"})

@pytest.mark.asyncio
async def test_pdf_client_runtime_error():
    client = PDFGeneratorClient()
    with patch("httpx.AsyncClient.post", side_effect=Exception("Unknown Error")):
        with pytest.raises(RuntimeError, match="runtime error: Unknown Error"):
            await client.generate_pdf({"username": "Admin"})
