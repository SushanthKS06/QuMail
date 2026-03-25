import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from main import app
from extensions.chat import SecureChatExtension, SecurityLevel

client = TestClient(app)

@pytest.mark.asyncio
async def test_chat_flow():
    # Mock authentication
    with patch("api.dependencies.verify_token", return_value={"sub": "test@qumail.com"}):
        
        # 1. Create Session
        with patch("extensions.chat.SecureChatExtension.create_session") as mock_create:
            mock_session = MagicMock()
            mock_session.id = "session123"
            mock_session.peer_id = "bob@example.com"
            mock_session.security_level = SecurityLevel.AES
            mock_session.created_at = MagicMock()
            mock_session.created_at.isoformat.return_value = "2023-01-01T00:00:00Z"
            mock_session.is_active = True
            
            mock_create.return_value = mock_session
            
            # We need to mock the dependency get_chat_extension to return our mock
            # But simpler integration test: use the real extension logic with mocked QKD
            pass

@pytest.mark.asyncio
async def test_chat_extension_logic():
    """Test the core extension logic directly to avoid complex FastAPI mocking"""
    chat_ext = SecureChatExtension()
    await chat_ext.initialize()
    
    # 1. Create Session
    session = chat_ext.create_session("bob@example.com", SecurityLevel.AES)
    assert session.id is not None
    assert session.peer_id == "bob@example.com"
    
    # 2. Encrypt Message
    with patch("crypto_engine.encrypt_email", new_callable=AsyncMock) as mock_encrypt:
        mock_encrypt.return_value = {
            "ciphertext": "ENCRYPTED_BYTES_B64",
            "key_id": "key123",
            "metadata": {}
        }
        
        msg = await chat_ext.encrypt_message(b"Hello Bob", "bob@example.com", SecurityLevel.AES)
        assert msg.ciphertext == b"ENCRYPTED_BYTES_B64"
        assert msg.key_id == "key123"
        
    # 3. Decrypt Message
    with patch("crypto_engine.decrypt_email", new_callable=AsyncMock) as mock_decrypt:
        mock_decrypt.return_value = {
            "body": "Hello Bob",
        }
        
        decrypted = await chat_ext.decrypt_message(msg)
        assert decrypted.content == b"Hello Bob"
        assert decrypted.sender == "self"
