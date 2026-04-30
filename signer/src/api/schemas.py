from pydantic import BaseModel, HttpUrl, Field

class SignRequest(BaseModel):
    """Схема запроса для подписания документа"""
    dockument_base64: str = Field(
        ...,
        title='PDF документ',
        description='base64 кодированный PDF документ'
    )
    text_url: HttpUrl = Field(
        ...,
        title='URL текста подписи',
        description='Ссылка на публичный шаблон текста для подписи'
    )
    img_url: HttpUrl = Field(
        ...,
        title='URL изображения печати',
        description='Ссылка на публичный шаблон печати для подписи'
    )

class SignResponse(BaseModel):
    signed_dockument_base64: str = Field(
        ...,
        title='Подписанный PDF документ',
        description='base64 кодированный подписанный PDF документ'
    )
