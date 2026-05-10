import httpx
import base64
from fastapi import HTTPException
from src.core.config import settings

class PDFGeneratorClient:
    """ Проксирование запросов на генерацию отчета
    """

    async def generate_pdf(self, payload: dict) -> bytes:
        url = f'{settings.PDF_GEN_API_URL}/api/v1/generate'

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)

                if response.status_code != 200:
                    error_detail = response.json().get('detail', 'runtime error')
                    raise RuntimeError(error_detail)
                
                b64_data = response.json().get('pdf_base64', '')
                return base64.b64decode(b64_data)
        
        except httpx.HTTPError as e:
            raise HTTPException(status_code=500, detail=f'Generator connection failed: {str(e)}')

        except Exception as e:
            raise HTTPException(status_code=500, detail=f'runtime error: {str(e)}')
