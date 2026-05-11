import pytest
import base64
from aiohttp import web, ClientError
from aioresponses import aioresponses
import urllib.parse
import random
import string
from unittest.mock import patch

from src.services.fetcher import SignatureAssetFetcher
from src.core.config import settings
from src.core.exceptions import (
    SecurityError,
    InvalidPayloadError,
    PayloadTooLargeError,
    NetworkError
)

@pytest.fixture
def fetcher() -> SignatureAssetFetcher:
    return SignatureAssetFetcher()

def generate_random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@pytest.mark.parametrize("scheme", ["http", "https"])
@pytest.mark.parametrize("path_template", [
    "/public/assets/{rand}",
    "/api/v1/data/{rand}",
    "/internal_{rand}/file",
    "/{rand}_internal/file",
    "/InTeRnAl_{rand}/",
    "/",
    "/{rand}/..s/file"
])
def test_waf_allows_valid_and_similar_urls(fetcher, scheme, path_template):
    path = path_template.format(rand=generate_random_string())
    query = f"?q={generate_random_string()}"
    url = f"{scheme}://storage.local{path}{query}#fragment"
    
    fetcher._check_waf_rules(url)


def test_waf_allows_encoded_valid_urls(fetcher):
    base_path = f"/public/safe_{generate_random_string()}"
    
    enc1 = urllib.parse.quote(base_path)
    fetcher._check_waf_rules(f"http://test.com{enc1}")
    
    enc2 = urllib.parse.quote(enc1)
    fetcher._check_waf_rules(f"http://test.com{enc2}")


def test_waf_unquote_loop_break_condition(fetcher):
    url = f"http://test.com/public/{generate_random_string()}%ZZ"
    fetcher._check_waf_rules(url)

@patch('urllib.parse.urlparse')
def test_waf_blocks_malformed_url(mock_urlparse, fetcher):
    mock_urlparse.side_effect = Exception("Critical Parsing Error")
    
    with pytest.raises(SecurityError, match="WAF: Malformed URL structure."):
        fetcher._check_waf_rules("http://anything.com")


@pytest.mark.parametrize("bad_scheme", ["ftp", "file", "ws", "gopher", "mailto", ""])
def test_waf_blocks_invalid_schemes(fetcher, bad_scheme):
    url = f"{bad_scheme}://test.com/public" if bad_scheme else "test.com/public"
    with pytest.raises(SecurityError, match="WAF: Only HTTP/HTTPS schemes are allowed."):
        fetcher._check_waf_rules(url)


def test_waf_blocks_over_encoded_urls(fetcher):
    base_path = "public/safe data"
    
    enc1 = urllib.parse.quote(base_path)
    enc2 = urllib.parse.quote(enc1)
    enc3 = urllib.parse.quote(enc2)
    
    url = f"http://test.com/{enc3}"
    
    with pytest.raises(SecurityError, match="WAF: URL is over-encoded."):
        fetcher._check_waf_rules(url)


@pytest.mark.parametrize("bad_char", ["привет", "ñ", "©"])
def test_waf_blocks_non_ascii(fetcher, bad_char):
    url = f"http://test.com/public/{bad_char}"
    with pytest.raises(SecurityError, match="WAF: Non-ASCII characters are not allowed in URLs."):
        fetcher._check_waf_rules(url)


def test_waf_blocks_matrix_parameters(fetcher):
    url = "http://test.com/public/asset%3Bparam=value"
    
    with pytest.raises(SecurityError, match="WAF: Matrix parameters are not allowed."):
        fetcher._check_waf_rules(url)

@pytest.mark.parametrize("internal_payload", [
    "/internal",
    "/internal/",
    "/INTERNAL/secret",
    "/InTeRnAl/secret",
    "/public/../internal/secret",
    "/public/..\\internal\\secret",
    "/public/..%2finternal/secret",
    "/public/%2e%2e/internal/secret",
    "/%252finternal/secret"
])
def test_waf_blocks_internal_paths_and_traversals(fetcher, internal_payload):
    url = f"http://test.com{internal_payload}"
    with pytest.raises(SecurityError, match="WAF: Cannot fetch from this path."):
        fetcher._check_waf_rules(url)

@pytest.mark.asyncio
async def test_ssrf_token_leak_via_redirect(fetcher: SignatureAssetFetcher):
    captured_headers = {}
    expected_bytes = b'secret_data'

    async def attacker_redirect_handler(request: web.Request) -> web.Response:
        captured_headers.update(request.headers)

        raise web.HTTPFound('/internal/secret')
    
    async def internal_handler(request: web.Request) -> web.Response:
        captured_headers.update(request.headers)
        b64_payload = base64.b64encode(expected_bytes).decode('utf-8')

        return web.json_response({'data': b64_payload})

    app = web.Application()
    app.router.add_get('/bypass', attacker_redirect_handler)
    app.router.add_get('/internal/secret', internal_handler)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, '127.0.0.1', 0)
    await site.start()

    try:
        port = runner.addresses[0][1]
        attacker_url = f'http://127.0.0.1:{port}/bypass'

        result = await fetcher.fetch(attacker_url, is_user_provided=True)

        assert result == expected_bytes
        assert captured_headers.get('X-Service-Token') == settings.SIGNER_TOKEN
    
    finally:
        await runner.cleanup()

@pytest.mark.asyncio
async def test_fetch_end_decode_public(fetcher: SignatureAssetFetcher):
    url = 'http://storage/public/public-data'
    expected_bytes = b'public_data'
    b64_payload = base64.b64encode(expected_bytes).decode('utf-8')

    with aioresponses() as m:
        m.get(url, status=200, payload={'data': b64_payload})
        result = await fetcher.fetch(url)
        assert result == expected_bytes

@pytest.mark.asyncio
async def test_payload_to_large(fetcher: SignatureAssetFetcher):
    url = 'http://storage/public/public-data'
    large_bytes = b'A' * (settings.MAX_DOCUMENT_SIZE + 1)
    b64_payload = base64.b64encode(large_bytes).decode('utf-8')

    with aioresponses() as m:
        m.get(url, status=200, payload={'data': b64_payload})
        with pytest.raises(PayloadTooLargeError, match='Response exceeds'):
            await fetcher.fetch(url)

@pytest.mark.asyncio
async def test_invalid_json_format_not_json(fetcher: SignatureAssetFetcher):
    url = 'http://storage/public/public-data'

    with aioresponses() as m:
        m.get(url, status=200, body='invalid') 
        with pytest.raises(InvalidPayloadError, match='Expected JSON'):
            await fetcher.fetch(url)

@pytest.mark.asyncio
async def test_invalid_json_format_missing_data(fetcher: SignatureAssetFetcher):
    url = 'http://storage/public/public-data'

    with aioresponses() as m:
        m.get(url, status=200, payload={'wrong': 'value'})
        with pytest.raises(InvalidPayloadError, match='Missing \'data\' field'):
            await fetcher.fetch(url)

@pytest.mark.asyncio
async def test_invalid_json_format_bad_base64(fetcher: SignatureAssetFetcher):
    url = 'http://storage/public/public-data'

    with aioresponses() as m:
        m.get(url, status=200, payload={'data': 'value'})
        with pytest.raises(InvalidPayloadError, match='Invalid base64 payload'):
            await fetcher.fetch(url)

@pytest.mark.asyncio
async def test_network_connection_error(fetcher: SignatureAssetFetcher):
    url = 'http://storage/public/public-data'

    with aioresponses() as m:
        m.get(url, exception=ClientError())
        with pytest.raises(NetworkError):
            await fetcher.fetch(url)

@pytest.mark.asyncio
async def test_http_status_error(fetcher: SignatureAssetFetcher):
    url = 'http://storage/public/public-data'

    with aioresponses() as m:
        m.get(url, status=500) 
        with pytest.raises(NetworkError, match='HTTP Request failed'):
            await fetcher.fetch(url)
