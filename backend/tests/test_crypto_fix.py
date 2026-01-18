import asyncio
import pytest
import sys
import os
import base64
import json
from unittest.mock import MagicMock, AsyncMock, patch

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from crypto_engine import encrypt_email, decrypt_email, decrypt_attachment
from crypto_engine.otp import otp_encrypt

@pytest.mark.asyncio
async def test_encrypt_email_otp_attachment():
    # Mock dependencies
    with patch("qkd_client.request_key") as mock_request:
        # Mock key responses
        mock_request.side_effect = [
            # 1. Body key
            {"key_id": "k1", "key_material": b"x" * 10},
            # 2. Attachment key
            {"key_id": "k2", "key_material": b"y" * 10}
        ]
        
        body = "helloworld"
        att_content = b"attachment"
        
        result = await encrypt_email(
            body=body,
            security_level=1,
            recipients=["bob"],
            attachments=[{"filename": "test.txt", "content": att_content}]
        )
        
        # Verify attachment is encrypted
        att_result = result["attachments"][0]
        enc_content = att_result["content"]
        
        # Should be base64 encoded JSON
        envelope = json.loads(base64.b64decode(enc_content))
        
        assert envelope["security_level"] == 1
        assert envelope["key_id"] == "k2"
        assert envelope["ciphertext"] != base64.b64encode(att_content).decode('ascii')
        
        # Verify decryption flow
        with patch("qkd_client.get_key") as mock_get_key:
            mock_get_key.side_effect = [
                {"key_id": "k2", "key_material": b"y" * 10}
            ]
            
            decrypted = await decrypt_attachment(enc_content, "k1", 1)
            assert decrypted == att_content

@pytest.mark.asyncio
async def test_encrypt_email_aes_attachment():
    with patch("qkd_client.request_key") as mock_request, \
         patch("qkd_client.get_key") as mock_get_key:
             
        mock_request.return_value = {"key_id": "k3", "key_material": b"seed" * 8}
        
        body = "helloworld"
        att_content = b"attachment_aes"
        
        result = await encrypt_email(
            body=body,
            security_level=2,
            recipients=["bob"],
            attachments=[{"filename": "test.txt", "content": att_content}]
        )
        
        att_result = result["attachments"][0]
        enc_content = att_result["content"]
        
        # Decryption
        mock_get_key.return_value = {"key_id": "k3", "key_material": b"seed" * 8}
        decrypted = await decrypt_attachment(enc_content, "k3", 2)
        assert decrypted == att_content
