import pytest
from unittest.mock import AsyncMock
from httpx import AsyncClient, ASGITransport
from src.main import app
from src.api.generate import get_generator_service
from src.services.renderer import PDFGeneratorService

@pytest.fixture
def mock_generator():
    return AsyncMock(spec=PDFGeneratorService)

@pytest.fixture
async def client(mock_generator):
    app.dependency_overrides[get_generator_service] = lambda: mock_generator
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
        
    app.dependency_overrides.clear()

@pytest.fixture
def valid_payload():
    return {
        "username": "ctf_user",
        "team": "PwnTeam",
        "score": 1000,
        "tasks": [
            {
                "title": "Web - Secure Gateway",
                "score": 500,
                "attempts": 1,
                "comment": "Easy task!"
            }
        ]
    }

@pytest.mark.asyncio
async def test_health_check_returns_ok(client):
    response = await client.get("/health")
    
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_generate_report_endpoint_success(client, mock_generator, valid_payload):
    mock_generator.generate_signed_report.return_value = "signed_pdf_b64"
    
    response = await client.post("/api/v1/generate", json=valid_payload)
    
    assert response.status_code == 200
    assert response.json() == {"pdf_base64": "signed_pdf_b64"}
    mock_generator.generate_signed_report.assert_called_once()


@pytest.mark.asyncio
async def test_generate_report_endpoint_handles_exceptions(client, mock_generator, valid_payload):
    error_message = "Storage service is unreachable"
    mock_generator.generate_signed_report.side_effect = Exception(error_message)
    
    response = await client.post("/api/v1/generate", json=valid_payload)
    assert response.status_code == 500
    assert response.json()["detail"] == f"Generation Failed: {error_message}"


@pytest.mark.asyncio
async def test_generate_report_endpoint_validation_error(client):
    bad_payload = {
        "username": "ctf_user",
        # Отсутствуют обязательные поля team, score, tasks
    }
    
    response = await client.post("/api/v1/generate", json=bad_payload)
    
    assert response.status_code == 422