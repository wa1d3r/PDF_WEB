from pydantic import BaseModel, Field

class DataResponse(BaseModel):
    """Схема ответа"""

    data: bytes = Field(
        ...,
        title='Данные файла',
        description=(
            'Сериализованные бинарные данные файла'
        )
    )
