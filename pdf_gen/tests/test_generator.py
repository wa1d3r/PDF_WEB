import pytest
import base64
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from src.services.renderer import PDFGeneratorService, parse_user_macros
from src.services.clients import StorageClient, SignerClient
from src.api.schemas import CTFdReportData, TaskResult
from src.core.exceptions import NetworkError

def test_parse_macros_ssti_logic():
    assert parse_user_macros("{{ 7 * 7 }}") == "49"
    
    result = parse_user_macros("{{ ''.__class__.__name__ }}")
    assert result == "str"
    
    bad_template = "{{ invalid.syntax }"
    assert parse_user_macros(bad_template) == bad_template
    
    assert parse_user_macros("") == ""
    assert parse_user_macros(None) == ""


@pytest.fixture
def mock_storage():
    return AsyncMock(spec=StorageClient)

@pytest.fixture
def mock_signer():
    return AsyncMock(spec=SignerClient)

@pytest.fixture
def generator(mock_storage, mock_signer):
    return PDFGeneratorService(mock_storage, mock_signer)

@pytest.fixture
def sample_report_data():
    return CTFdReportData(
        username="ctf_user",
        team="PwnTeam",
        score=1000,
        tasks=[
            TaskResult(title="Web", score=500, attempts=1, comment="{{ 7 * 7 }}"),
            TaskResult(title="Pwn", score=500, attempts=2, comment="No macro")
        ]
    )

@pytest.mark.asyncio
async def test_generate_signed_report_success(generator, mock_storage, mock_signer, sample_report_data):
    html_content = "<html><body>{{ data.username }} - {% for t in data.tasks %}{{ t.comment | parse_macros }}{% endfor %}</body></html>"
    mock_storage.get_template.return_value = html_content
    mock_signer.sign_pdf.return_value = "signed_data"

    with patch("src.services.renderer.HTML") as mock_html:
        mock_html_instance = mock_html.return_value
        mock_html_instance.write_pdf.return_value = b"pdf_bytes"
        
        result = await generator.generate_signed_report(sample_report_data)

        assert result == "signed_data"
        
        called_html = mock_html.call_args[1]['string']
        assert "ctf_user" in called_html
        assert "49" in called_html
        
        mock_storage.get_template.assert_called_once_with("report.html")
        expected_b64 = base64.b64encode(b"pdf_bytes").decode('utf-8')
        mock_signer.sign_pdf.assert_called_once_with(expected_b64)


@pytest.mark.asyncio
async def test_generate_report_storage_failure(generator, mock_storage):
    mock_storage.get_template.side_effect = NetworkError("Storage Down")
    
    with pytest.raises(NetworkError, match="Storage Down"):
        await generator.generate_signed_report(MagicMock())


@pytest.mark.asyncio
async def test_generate_report_signer_failure(generator, mock_storage, mock_signer):
    mock_storage.get_template.return_value = "<html></html>"
    mock_signer.sign_pdf.side_effect = NetworkError("Signer Down")
    
    with patch("src.services.renderer.HTML") as mock_html:
        mock_html.return_value.write_pdf.return_value = b"FAKE_PDF_BYTES"
        
        with pytest.raises(NetworkError, match="Signer Down"):
            await generator.generate_signed_report(MagicMock())

@pytest.mark.asyncio
async def test_storage_client_decoding():
    client = StorageClient()
    template_html = "<h1>Test</h1>"
    encoded_html = base64.b64encode(template_html.encode()).decode()
    
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"data": encoded_html}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        result = await client.get_template("any.html")
        assert result == template_html

@pytest.mark.asyncio
async def test_signer_client_payload_structure():
    client = SignerClient()
    pdf_input = "BASE64_IN"
    
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"signed_document_base64": "BASE64_OUT"}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", return_value=mock_resp) as mock_post:
        result = await client.sign_pdf(pdf_input)
        
        sent_json = mock_post.call_args[1]['json']
        assert sent_json["document_base64"] == pdf_input
        assert "stamp_text" in sent_json["text_url"] 
        assert result == "BASE64_OUT"

@pytest.mark.asyncio
async def test_storage_client_network_error():
    client = StorageClient()
    
    with patch("httpx.AsyncClient.get", side_effect=httpx.RequestError("Connection timeout")):
        with pytest.raises(NetworkError, match="Storage API error"):
            await client.get_template("report.html")


@pytest.mark.asyncio
async def test_signer_client_network_error():
    client = SignerClient()
    
    with patch("httpx.AsyncClient.post", side_effect=httpx.RequestError("Connection refused")):
        with pytest.raises(NetworkError, match="Signer API error"):
            await client.sign_pdf("ANY_BASE64")