import json
from pathlib import Path
from src.core.config import settings

_storage_data: dict | None = None

def load_storage() -> dict:
    """Синхронно загружает JSON-файл в память.

    Returns:
        dict: Загруженный словарь
    """
    global _storage_data
    if _storage_data is None:
        path = Path(settings.STORAGE_FILE_PATH)
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                _storage_data = json.load(f)
        else:
            _storage_data = {"public": {}, "internal": {}}
    return _storage_data

async def get_storage() -> dict:
    """Зависимость FastAPI для получения доступа к данным хранилища.

    Returns:
        dict: Словарь с данными из JSON файла.
    """
    return load_storage()
