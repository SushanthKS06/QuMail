import asyncio
import os
import sys
from pathlib import Path

import pytest

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

os.environ.setdefault("QUMAIL_SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("QUMAIL_API_TOKEN", "test-api-token")
os.environ.setdefault("KM_URL", "http://127.0.0.1:8100")


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_plaintext():
    return b"Hello, this is a test message for QuMail encryption testing!"


@pytest.fixture
def sample_plaintext_str():
    return "Hello, this is a test message for QuMail encryption testing!"


@pytest.fixture
def large_plaintext():
    return os.urandom(10000)


@pytest.fixture
def aes_key():
    return os.urandom(32)


@pytest.fixture
def otp_key(sample_plaintext):
    return os.urandom(len(sample_plaintext))


@pytest.fixture
def short_key():
    return os.urandom(10)


@pytest.fixture
def mock_key_response():
    return {
        "key_id": "test-key-id-12345",
        "key_material": os.urandom(32),
        "peer_id": "test@example.com",
        "key_type": "aes_seed",
    }


@pytest.fixture
def mock_otp_key_response(sample_plaintext):
    return {
        "key_id": "test-otp-key-id-12345",
        "key_material": os.urandom(len(sample_plaintext)),
        "peer_id": "test@example.com",
        "key_type": "otp",
    }


@pytest.fixture
def sample_email_data():
    return {
        "to": ["recipient@example.com"],
        "cc": [],
        "subject": "Test Email",
        "body": "This is a test email body.",
        "security_level": 2,
    }


@pytest.fixture
def sample_recipients():
    return ["alice@example.com", "bob@example.com"]
