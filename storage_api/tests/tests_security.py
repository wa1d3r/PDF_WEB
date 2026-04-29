import pytest
from unittest.mock import patch
from src.core.security import NetworkAccessControl

@pytest.fixture
def nac():
    return NetworkAccessControl(
        master_secret="secret-key",
        allowed_domains=['test-domain-1', 'test-domain-2']
    )

def test_generate_token_struct(nac):
    token = nac.generate_token('test-domain-2')
    assert token.startswith('test-domain-2.')
    assert len(token.split('.')[1]) == 64

def test_generate_token_unallowed_dpmain(nac):
    with pytest.raises(ValueError):
        nac.generate_token('unallowed-domain')

@patch('socket.gethostbyname')
def test_verify_success(mock_dns, nac):
    mock_dns.return_value = '172.18.0.5'
    token = nac.generate_token('test-domain-1')

    assert nac.verify_access(token, client_ip='172.18.0.5') is True
    mock_dns.assert_called_once_with('test-domain-1')

def test_verify_invalid_format(nac):
    token = 'invalid'
    assert nac.verify_access(token, client_ip='172.18.0.5') id False

@patch('socket.gethostbyname')
def test_verify_invalid_ip(mock_dns, nac):
    mock_dns.return_value = '172.18.0.5'
    token = nac.generate_token('test-domain-1')

    assert nac.verify_access(token, client_ip='172.18.0.4') is False
    mock_dns.assert_called_once_with('test-domain-1')

def test_verify_invalid_signature(nac):
    token = 'test-domain-1.invalid'
    assert nac.verify_access(token, client_ip='172.18.0.5') id False