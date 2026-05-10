import pytest
import base64
import httpx
from fastapi import HTTPException
from unittest.mock import patch, MagicMock

from src.services.storage_client import StorageClient
from src.services.ctfd_client import CTFdClient
from src.services.pdf_client import PDFGeneratorClient
from src.core.exceptions import NetworkError


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
async def test_ctfd_client_success():
    client = CTFdClient()
    fake_data = {"username": "hacker", "score": 100}
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"data": fake_data}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        result = await client.fetch_user_data("valid_token")
        assert result == fake_data

@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [401, 403])
async def test_ctfd_client_auth_error(status_code):
    client = CTFdClient()
    mock_resp = MagicMock()
    mock_resp.status_code = status_code

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        with pytest.raises(ValueError, match="Invalid or expired"):
            await client.fetch_user_data("bad_token")

@pytest.mark.asyncio
async def test_ctfd_client_network_error():
    client = CTFdClient()
    with patch("httpx.AsyncClient.get", side_effect=httpx.RequestError("Down")):
        with pytest.raises(NetworkError, match="currently unavailable"):
            await client.fetch_user_data("token")

@pytest.mark.asyncio
async def test_pdf_client_success():
    client = PDFGeneratorClient()
    fake_pdf_bytes = b"PDF_CONTENT"
    b64_pdf = base64.b64encode(fake_pdf_bytes).decode()
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"pdf_base64": b64_pdf}

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        result = await client.generate_pdf({"user": "test"})
        assert result == fake_pdf_bytes

@pytest.mark.asyncio
async def test_pdf_client_generator_error():
    client = PDFGeneratorClient()
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.json.return_value = {"detail": "Jinja2 Syntax Error"}

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="runtime error: Jinja2 Syntax Error"):
            await client.generate_pdf({"user": "test"})

@pytest.mark.asyncio
async def test_pdf_client_network_error():
    client = PDFGeneratorClient()
    with patch("httpx.AsyncClient.post", side_effect=httpx.RequestError("Down")):
        with pytest.raises(NetworkError, match="connection failed"):
            await client.generate_pdf({"user": "test"})
