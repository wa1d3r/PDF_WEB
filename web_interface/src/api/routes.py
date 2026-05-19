import io
import logging
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

from src.api.schemas import ManualReportRequest
from src.services.pdf_client import PDFGeneratorClient
from src.services.storage_client import StorageClient
from src.core.template import engine

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Web Interface"])

StorageDep = Annotated[StorageClient, Depends()]
PDFDep = Annotated[PDFGeneratorClient, Depends()]

@router.get("/", response_class=HTMLResponse)
async def index(storage: StorageDep):
    logger.info("Rendering index page...")
    template_str = await storage.get_template("web_index.html")
    return HTMLResponse(content=engine.render_from_string(template_str, {}))

@router.get("/admin", response_class=HTMLResponse)
async def admin_page(storage: StorageDep):
    logger.info("Rendering admin page...")
    template_str = await storage.get_template("web_admin.html")
    return HTMLResponse(content=engine.render_from_string(template_str, {}))

@router.post("/api/admin/preview", response_class=HTMLResponse)
async def admin_preview(
    body: ManualReportRequest,
    storage: StorageDep
):
    logger.info(f"Processing admin preview request for {body.username}...")
    try:
        template_str = await storage.get_template("web_dashboard.html")
        rendered_html = engine.render_from_string(template_str, {"data": body.model_dump()})
        return HTMLResponse(content=rendered_html)
    
    except Exception as e:
        logger.error(f"Preview failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/admin/export")
async def admin_export(
    body: ManualReportRequest,
    pdf_gen: PDFDep
):
    logger.info(f"Processing admin PDF export request for {body.username}...")
    try:
        pdf_bytes = await pdf_gen.generate_pdf(body.model_dump())
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=manual_report.pdf"}
        )
    
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
