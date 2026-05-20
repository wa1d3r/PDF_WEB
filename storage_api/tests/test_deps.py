import pytest
from fastapi import Request, HTTPException
from src.api.deps import verify_service_access

@pytest.mark.asyncio
async def test_deps_missing_token():
    req = Request({"type": "http", "client": None, "query_string": b""})
    with pytest.raises(HTTPException) as exc:
        await verify_service_access(req, x_service_token=None)
    assert exc.value.status_code == 401
    assert "Missing X-Service-Token" in exc.value.detail

@pytest.mark.asyncio
async def test_deps_nac_blocks(mocker):
    req = Request({"type": "http", "client": ("127.0.0.1", 8000), "query_string": b""})
    mocker.patch("src.api.deps.nac.verify_access", return_value=False)
    
    with pytest.raises(HTTPException) as exc:
        await verify_service_access(req, x_service_token="fake.token")
    assert exc.value.status_code == 401
    assert "Invalid or unauthorized token" in exc.value.detail

@pytest.mark.asyncio
async def test_deps_success(mocker):
    req = Request({"type": "http", "client": ("127.0.0.1", 8000), "query_string": b""})
    mocker.patch("src.api.deps.nac.verify_access", return_value=True)
    
    token = await verify_service_access(req, x_service_token="valid.token")
    assert token == "valid.token"