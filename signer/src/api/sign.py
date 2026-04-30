import base64
from typing import Annotated
from fastapi import APIRouter, HTTPException, Depends
from src.core.config import settings
from src.api.schemas import SignRequest, SignResponse
from src.services.fetcher import SignatureAssetFetcher
from src.services.crypto import PDFCryptoSigner
from src.core.exceptions import (
    SecurityError,
    InvalidPayloadError,
    PayloadTooLargeError,
    NetworkError
)

router = APIRouter(prefix='/api/v1', tags=['Signature API'])

@router.post(
    '/sign',
    response_model=SignResponse,
    summary='Подписать PDF документ',
    description='Загружает публичные ресурсы, ключ подписи и накладывает ЭЦП'
)
async def sign_document(
    payload: SignRequest,
    fetcher: Annotated[SignatureAssetFetcher, Depends()],
    crypto: Annotated[PDFCryptoSigner, Depends()]
) -> SignRequest:
    try:
        text_bytes = await fetcher.fetch(str(payload.text_url))
        image_bytes = await fetcher.fetch(str(payload.img_url))
        p12_bytes = await fetcher.fetch(settings.PRIVATE_KEY_URL, is_user_provided=False)

        pdf_bytes = base64.b64decode(payload.document_base64)
        sig_text = text_bytes.decode('utf-8').strip()

        signed_pdf_bytes = await crypto.apply_signature(
            document_bytes=pdf_bytes,
            pkcs12_bytes=p12_bytes,
            password=settings.PRIVATE_KEY_PASSWORD,
            signature_text=sig_text,
            image_bytes=image_bytes
        )

        return SignResponse(
            signed_document_base64=base64.b64encode(signed_pdf_bytes).decode('utf-8')
        )
    
    except SecurityError as e:
        raise HTTPException(status_code=403, detail=str(e))
    
    except (InvalidPayloadError, PayloadTooLargeError, ValueError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    
    except NetworkError as e:
        raise HTTPException(status_code=502, detail=str(e))
    