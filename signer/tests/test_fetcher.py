import pytest
import base64
from aiohttp import web, ClientError
from aioresponses import aioresponses

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

@pytest.mark.asyncio
async def test_waf_blocks_internal_direct_access(fetcher: SignatureAssetFetcher):
    url = 'http://storage/internal/secret/secret-data'

    with pytest.raises(SecurityError, match='WAFException: Cannot fetch from /internal/ paths.'):
        await fetcher.fetch(url, is_user_provided=True)

@pytest.mark.asyncio
async def test_waf_allows_internal_for_system(fetcher: SignatureAssetFetcher):
    url = 'http://storage/internal/secret/secret-data'
    expected_bytes = b'secret_data'
    b64_payload = base64.b64encode(expected_bytes).decode('utf-8')

    with aioresponses() as m:
        m.get(url, status=200, payload={'data': b64_payload})
        result = await fetcher.fetch(url, is_user_provided=False)
        assert result == expected_bytes

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
async def test_invalid_json_format(fetcher: SignatureAssetFetcher):
    url = 'http://storage/public/public-data'

    with aioresponses() as m:
        m.get(url, status=200, payload='invalid')
        with pytest.raises(InvalidPayloadError, match='Expected JSON'):
            await fetcher.fetch(url)

@pytest.mark.asyncio
async def test_invalid_json_format(fetcher: SignatureAssetFetcher):
    url = 'http://storage/public/public-data'

    with aioresponses() as m:
        m.get(url, status=200, payload={'wrong': 'value'})
        with pytest.raises(InvalidPayloadError, match='Missing \'data\' field'):
            await fetcher.fetch(url)

@pytest.mark.asyncio
async def test_invalid_json_format(fetcher: SignatureAssetFetcher):
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
        m.get(url, exception=ClientError())
        with pytest.raises(NetworkError):
            await fetcher.fetch(url)