import io
import hashlib
import logging
from functools import lru_cache
from PIL import Image
from pyhanko import stamp
from pyhanko.pdf_utils import images, text
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign import signers, fields

logger = logging.getLogger(__name__)

class PDFCryptoSigner:
    """Сервис наложения визуального штампа и ЭЦП с использованием pyHanko.
    """

    @staticmethod
    @lru_cache(maxsize=3)
    def _parse_pkcs12(pkcs12_bytes: bytes, password: str) -> signers.SimpleSigner:
        logger.info("Parsing new PKCS#12 container...")
        return signers.SimpleSigner.load_pkcs12_data(
            pkcs12_bytes,
            other_certs=None,
            passphrase=password.encode('utf-8')
        )

    def _get_signer(self, pkcs12_bytes: bytes, password: str) -> signers.SimpleSigner:
        """Извлекает подписанта из кэша или инициализирует нового.

        Args:
            pkcs12_bytes (bytes): Бинарные данные сертификата (PKCS#12/PFX).
            password (str): Пароль для расшифровки.

        Raises:
            ValueError: При неверном пароле или поврежденном контейнере.

        Returns:
            signers.SimpleSigner: Готовый к работе объект подписанта pyHanko.
        """
        try:
            signer = self._parse_pkcs12(pkcs12_bytes, password)
            logger.info("PKCS#12 Signer loaded.")
            return signer
        except Exception as e:
            logger.error(f"Failed to load PKCS#12 data: {e}")
            raise ValueError("Invalid PKCS#12 container or wrong password")
    
    async def apply_signature(
            self,
            document_bytes: bytes,
            pkcs12_bytes: bytes,
            password: str,
            signature_text: str,
            image_bytes: bytes
    ) -> bytes:
        """Асинхронно осуществляет криптографическую подпись PDF документа.

        Args:
            document_bytes (bytes): Исходный PDF документ.
            pkcs12_bytes (bytes): Бинарные данные сертификата (PKCS#12/PFX).
            password (str): Пароль для расшифровки контейнера сертификата.
            signature_text (str): Текст для штампа.
            image_bytes (bytes): Изображение печати

        Raises:
            ValueError: При ошибке парсинга PDF или криптографическом сбое.

        Returns:
            bytes: Подписанный PDF документ со встроенным визуальным штампом.
        """
        logger.info("Starting cryptographic signature process...")
        try:
            signer = self._get_signer(pkcs12_bytes, password)
            pdf_stream = io.BytesIO(document_bytes)
            pdf_writer = IncrementalPdfFileWriter(pdf_stream)

            signature_field_name = 'PlatformSignature'

            fields.append_signature_field(
                pdf_writer,
                sig_field_spec=fields.SigFieldSpec(
                    signature_field_name,
                    box=(50, 50, 408, 250)
                )
            )

            image_stream = io.BytesIO(image_bytes)
            
            with Image.open(image_stream) as pil_image:
                bg_image = images.PdfImage(pil_image)

                stamp_style = stamp.TextStampStyle(
                    stamp_text=f'{signature_text}\nSigned by: %(signer)s\nTime: %(ts)s',
                    background=bg_image,
                    border_width=0,
                    text_box_style=text.TextBoxStyle(
                        text_color=(1, 1, 1)
                    )
                )

                meta = signers.PdfSignatureMetadata(field_name=signature_field_name)
                pdf_signer = signers.PdfSigner(
                    signature_meta=meta,
                    signer=signer,
                    stamp_style=stamp_style
                )

                await pdf_signer.async_sign_pdf(pdf_writer, in_place=True)

                logger.info("PDF document successfully signed.")
                return pdf_stream.getvalue()

        except Exception as e:
            logger.exception("Signature process failed with an exception")
            
            if not isinstance(e, ValueError):
                raise ValueError(f'Failed to sign document: {str(e)}') from e
            raise e
