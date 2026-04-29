from base64 import b64encode
from pydantic import BaseModel, Field, field_serializer

class DataResponse(BaseModel):
    """Схема ответа"""

    data: bytes = Field(
        ...,
        title='Данные файла',
        description=(
            'Сериализованные бинарные данные файла'
        )
    )

    @field_serializer('data')
    def bytes_to_base64(self, data: bytes, _info) -> str:
        return b64encode(data).decode('utf-8')
