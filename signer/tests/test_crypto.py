import pytest
import io
import hashlib
import datetime
from reportlab.pdfgen import canvas
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.x509.oid import NameOID
import cryptography.x509 as x509
from asn1crypto import x509 as asn1_x509
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.validation import async_validate_pdf_signature
from pyhanko_certvalidator import ValidationContext
from cryptography.hazmat.primitives.serialization import pkcs12

from src.services.crypto import PDFCryptoSigner


@pytest.fixture(scope="session")
def valid_pdf_bytes() -> bytes:
    packet = io.BytesIO()
    c = canvas.Canvas(packet)
    c.drawString(100, 100, "Test Document for sign")
    c.save()
    return packet.getvalue()


@pytest.fixture(scope="session")
def dummy_image_bytes() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00"
        b"\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )


@pytest.fixture(scope="session")
def crypto_credentials() -> dict:
    password_str = "ctf_test_password"
    password_bytes = password_str.encode('utf-8')
    
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "CTF Testing Node"),
    ])
    
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        now_utc
    ).not_valid_after(
        now_utc + datetime.timedelta(days=10)
    ).sign(private_key, hashes.SHA256())
    
    p12_bytes = serialization.pkcs12.serialize_key_and_certificates(
        name=b"testing_cert",
        key=private_key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(password_bytes)
    )
    
    return {
        "p12_bytes": p12_bytes,
        "password": password_str
    }


@pytest.fixture(autouse=True)
def clear_crypto_cache():
    PDFCryptoSigner._signer_cache.clear()
    yield


@pytest.fixture
def crypto_signer() -> PDFCryptoSigner:
    return PDFCryptoSigner()



@pytest.mark.asyncio
async def test_apply_signature_success(
    crypto_signer: PDFCryptoSigner, 
    valid_pdf_bytes: bytes, 
    dummy_image_bytes: bytes, 
    crypto_credentials: dict
):
    signature_text = "test stamp"
    
    signed_pdf = await crypto_signer.apply_signature(
        document_bytes=valid_pdf_bytes,
        pkcs12_bytes=crypto_credentials["p12_bytes"],
        password=crypto_credentials["password"],
        signature_text=signature_text,
        image_bytes=dummy_image_bytes
    )
    
    assert isinstance(signed_pdf, bytes)
    assert signature_text.encode('utf-8') in signed_pdf
    
    _, cert, _ = pkcs12.load_key_and_certificates(
        crypto_credentials["p12_bytes"],
        crypto_credentials["password"].encode('utf-8')
    )
    
    cert_der = cert.public_bytes(serialization.Encoding.DER)
    asn1_cert = asn1_x509.Certificate.load(cert_der)
    
    vc = ValidationContext(trust_roots=[asn1_cert])
    
    reader = PdfFileReader(io.BytesIO(signed_pdf))
    assert len(reader.embedded_signatures) == 1
    sig_obj = reader.embedded_signatures[0]
    
    status = await async_validate_pdf_signature(sig_obj, signer_validation_context=vc)
    
    assert status.valid is True, "Криптографическая подпись недействительна!"
    assert status.intact is True, "Целостность PDF документа нарушена!"
    assert status.signing_cert.dump() == asn1_cert.dump()


@pytest.mark.asyncio
async def test_signer_cache_works_and_reuses_objects(
    crypto_signer: PDFCryptoSigner, 
    valid_pdf_bytes: bytes, 
    dummy_image_bytes: bytes, 
    crypto_credentials: dict
):
    p12_bytes = crypto_credentials["p12_bytes"]
    password = crypto_credentials["password"]
    expected_hash = hashlib.sha256(p12_bytes).hexdigest()
    
    assert len(PDFCryptoSigner._signer_cache) == 0

    await crypto_signer.apply_signature(
        valid_pdf_bytes, p12_bytes, password, "First", dummy_image_bytes
    )
    
    assert len(PDFCryptoSigner._signer_cache) == 1
    assert expected_hash in PDFCryptoSigner._signer_cache
    
    cached_signer_id = id(PDFCryptoSigner._signer_cache[expected_hash])

    await crypto_signer.apply_signature(
        valid_pdf_bytes, p12_bytes, password, "Second", dummy_image_bytes
    )
    
    assert len(PDFCryptoSigner._signer_cache) == 1
    assert id(PDFCryptoSigner._signer_cache[expected_hash]) == cached_signer_id


@pytest.mark.asyncio
async def test_invalid_password(
    crypto_signer: PDFCryptoSigner, 
    valid_pdf_bytes: bytes, 
    dummy_image_bytes: bytes, 
    crypto_credentials: dict
):
    with pytest.raises(ValueError, match="wrong password"):
        await crypto_signer.apply_signature(
            document_bytes=valid_pdf_bytes,
            pkcs12_bytes=crypto_credentials["p12_bytes"],
            password="wrong_password",
            signature_text="Test",
            image_bytes=dummy_image_bytes
        )


@pytest.mark.asyncio
async def test_corrupted_p12_container(
    crypto_signer: PDFCryptoSigner, 
    valid_pdf_bytes: bytes, 
    dummy_image_bytes: bytes
):
    with pytest.raises(ValueError, match="Invalid PKCS#12 container"):
        await crypto_signer.apply_signature(
            document_bytes=valid_pdf_bytes,
            pkcs12_bytes=b"wrong",
            password="any",
            signature_text="Test",
            image_bytes=dummy_image_bytes
        )


@pytest.mark.asyncio
async def test_corrupted_pdf_document(
    crypto_signer: PDFCryptoSigner, 
    dummy_image_bytes: bytes, 
    crypto_credentials: dict
):    
    with pytest.raises(ValueError, match="Failed to sign document"):
        await crypto_signer.apply_signature(
            document_bytes=b'wrong',
            pkcs12_bytes=crypto_credentials["p12_bytes"],
            password=crypto_credentials["password"],
            signature_text="Test",
            image_bytes=dummy_image_bytes
        )


@pytest.mark.asyncio
async def test_corrupted_image_bytes(
    crypto_signer: PDFCryptoSigner, 
    valid_pdf_bytes: bytes, 
    crypto_credentials: dict
):    
    with pytest.raises(ValueError, match="Failed to sign document"):
        await crypto_signer.apply_signature(
            document_bytes=valid_pdf_bytes,
            pkcs12_bytes=crypto_credentials["p12_bytes"],
            password=crypto_credentials["password"],
            signature_text="Test",
            image_bytes=b'wrong'
        )