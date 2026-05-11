from pydantic import BaseModel, Field

class DataResponse(BaseModel):
    """Схема ответа"""

    data: str = Field(
        ...,
        title='Данные файла',
        description='Base64 кодированные бинарные данные файла'
    )
