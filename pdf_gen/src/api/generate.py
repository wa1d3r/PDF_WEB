import logging
from typing import Annotated
from fastapi import APIRouter, HTTPException, Depends
from src.api.schemas import CTFdReportData, GenerateResponse
from src.services.renderer import PDFGeneratorService
from src.services.clients import StorageClient, SignerClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Generator"])

def get_generator_service() -> PDFGeneratorService:
    return PDFGeneratorService(StorageClient(), SignerClient())

@router.post(
    "/generate", 
    response_model=GenerateResponse,
    summary="Сгенерировать PDF отчет участника",
    description="Принимает JSON с данными участника, рендерит HTML в PDF и накладывает ЭЦП."
)
async def generate_report(
    payload: CTFdReportData,
    generator: Annotated[PDFGeneratorService, Depends(get_generator_service)]
) -> GenerateResponse:
    logger.info(f"Received generation request. User: {payload.username}, Tasks: {len(payload.tasks)}")
    try:
        signed_pdf_b64 = await generator.generate_signed_report(payload)
        logger.info(f"Successfully returning generated PDF for user '{payload.username}'.")
        return GenerateResponse(pdf_base64=signed_pdf_b64)
        
    except Exception as e:
        logger.error(f"Generation Pipeline Failed for user '{payload.username}': {str(e)}")
        raise HTTPException(status_code=500, detail=f"Generation Failed: {str(e)}")