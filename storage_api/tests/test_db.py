import pytest
from pathlib import Path
from src.db import json_storage

def test_load_storage_success(mocker):
    mocker.patch.object(Path, "exists", return_value=True)
    mocker.patch("builtins.open", mocker.mock_open(read_data='{"public": {"k": "v"}}'))
    
    data = json_storage.load_storage()
    assert data["public"]["k"] == "v"
    
    json_storage.load_storage()
    assert mocker.patch("builtins.open").call_count == 0

def test_load_storage_json_error(mocker):
    mocker.patch.object(Path, "exists", return_value=True)
    mocker.patch("builtins.open", mocker.mock_open(read_data='{bad_json}'))
    
    data = json_storage.load_storage()
    assert data == {"public": {}, "internal": {}}

def test_load_storage_file_not_found(mocker):
    mocker.patch.object(Path, "exists", return_value=False)
    
    data = json_storage.load_storage()
    assert data == {"public": {}, "internal": {}}

@pytest.mark.asyncio
async def test_get_storage_async_wrapper(mocker):
    mocker.patch("src.db.json_storage.load_storage", return_value={"test": "ok"})
    res = await json_storage.get_storage()
    assert res == {"test": "ok"}