import sys
import base64
import logging
from jinja2 import Environment
from weasyprint import HTML
from src.api.schemas import CTFdReportData
from src.services.clients import StorageClient, SignerClient

logger = logging.getLogger(__name__)

sys.setrecursionlimit(10000)

def parse_user_macros(comment_text: str) -> str:
    """Пользовательский фильтр для парсинга макросов.

    Args:
        comment_text (str): пользовательский комментарий с нагрузкой

    Returns:
        str: готовая часть html
    """
    if not comment_text:
        return ""
    try:
        return Environment().from_string(comment_text).render()
    except Exception as e:
        logger.warning(f"Macro parsing failed for {comment_text!r}. Error: {e}")
        return comment_text

class PDFGeneratorService:
    """Сервис генерации и подписания PDF отчетов."""
    
    def __init__(self, storage_client: StorageClient, signer_client: SignerClient):
        self.storage_client = storage_client
        self.signer_client = signer_client

    async def generate_signed_report(self, data: CTFdReportData) -> str:
        """Формирует отчет, конвертирует в PDF и отправляет на подписание.

        Args:
            data (CTFdReportData): Агрегированные данные игрока из CTFd.

        Returns:
            str: Подписанный PDF в формате Base64.
        """
        logger.info(f"Starting PDF generation process for user: '{data.username}' (Team: {data.team})")
        html_template = await self.storage_client.get_template("report.html")
        
        logger.info("Rendering HTML template with Jinja2...")
        env = Environment()
        env.filters['parse_macros'] = parse_user_macros
        
        
        template = env.from_string(html_template)
        rendered_html = template.render(data=data.model_dump())
        
        logger.info("Converting rendered HTML to PDF via WeasyPrint...")
        pdf_bytes = HTML(string=rendered_html).write_pdf()
        logger.info(f"PDF generated successfully. Size: {len(pdf_bytes)} bytes.")
        
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        signed_pdf_b64 = await self.signer_client.sign_pdf(pdf_base64)
        
        logger.info(f"Report generation pipeline completed for user '{data.username}'.")
        return signed_pdf_b64
