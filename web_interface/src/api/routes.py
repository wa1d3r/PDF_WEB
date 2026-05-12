import io
import logging
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

from src.api.schemas import TokenRequest
from src.services.ctfd_client import CTFdClient
from src.services.pdf_client import PDFGeneratorClient
from src.services.storage_client import StorageClient
from src.core.template import engine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Web Interface"])

StorageDep = Annotated[StorageClient, Depends()]
CTFdDep = Annotated[CTFdClient, Depends()]
PDFDep = Annotated[PDFGeneratorClient, Depends()]

@router.get("/", response_class=HTMLResponse)
async def index(storage: StorageDep):
    logger.info("Rendering index page...")
    template_str = await storage.get_template("web_index.html")
    rendered_html = engine.render_from_string(template_str, {})
    return HTMLResponse(content=rendered_html)

@router.post("/api/preview", response_class=HTMLResponse)
async def preview_report(
    body: TokenRequest,
    storage: StorageDep,
    ctfd: CTFdDep
):
    logger.info("Processing dashboard preview request...")
    try:
        data = await ctfd.fetch_user_data(body.token)
        template_str = await storage.get_template("web_dashboard.html")
        
        rendered_html = engine.render_from_string(template_str, {"data": data})
        return HTMLResponse(content=rendered_html)
        
    except ValueError as e:
        logger.warning(f"Preview access denied: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    
    except Exception as e:
        logger.warning(f"runtime error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/export")
async def export_pdf(
    body: TokenRequest,
    ctfd: CTFdDep,
    pdf_gen: PDFDep
):
    logger.info("Processing PDF export request...")
    try:
        data = await ctfd.fetch_user_data(body.token)
        
        pdf_bytes = await pdf_gen.generate_pdf(data)
        
        logger.info("Streaming PDF response back to client.")
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=report.pdf"}
        )
        
    except ValueError as e:
        logger.warning(f"Export access denied: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
