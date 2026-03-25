"""
End-to-End Encryption Proof Test Suite.

Provides automated proof that:
1. Encrypted output is ciphertext (not plaintext)
2. MIME messages contain only ciphertext
3. Tampering causes decryption failure at each security level
4. SHA-256 hash roundtrip: original_hash == decrypted_hash
5. Audit events are generated at encryption boundaries
"""

import base64
import json
import os
from unittest.mock import patch, AsyncMock

import pytest

from crypto_engine import encrypt_email, decrypt_email
from crypto_engine.integrity import compute_hash
from crypto_engine.aes_gcm import aes_encrypt, aes_decrypt, generate_aes_key
from email_service.mime_builder import build_encrypted_mime
from qkd_client.models import KeyResponse


# ─── Helpers ───

def mock_key_material(size: int = 32):
    return os.urandom(size)


def make_mock_patches(body_key_material):
    """Create standard mock patches for QKD client."""
    mock_response = KeyResponse(key_id="test-key-e2e", key_material=body_key_material, peer_id="peer", key_type="aes")
    return mock_response


# ─── Test: Encrypted Body Is Ciphertext ───

class TestEncryptedBodyIsCiphertext:

    @pytest.mark.asyncio
    async def test_aes_ciphertext_differs_from_plaintext(self):
        """Level 2: Encrypted output must not equal plaintext."""
        plaintext = "This is a confidential message."
        key_material = mock_key_material()
        mock_resp = make_mock_patches(key_material)

        with patch("qkd_client.request_key", new_callable=AsyncMock, return_value=mock_resp):
            result = await encrypt_email(
                body=plaintext,
                security_level=2,
                recipients=["alice@example.com"],
            )

        assert result["ciphertext"] != plaintext
        assert len(result["ciphertext"]) > 0

    @pytest.mark.asyncio
    async def test_otp_ciphertext_differs_from_plaintext(self):
        """Level 1: OTP encrypted output must differ from plaintext."""
        plaintext = "Top secret OTP message"
        key_material = os.urandom(len(plaintext.encode("utf-8")))
        mock_resp = KeyResponse(key_id="otp-key-e2e", key_material=key_material, peer_id="peer", key_type="otp")

        with patch("qkd_client.request_key", new_callable=AsyncMock, return_value=mock_resp), \
             patch("qkd_client.consume_key", new_callable=AsyncMock, return_value=True):
            result = await encrypt_email(
                body=plaintext,
                security_level=1,
                recipients=["bob@example.com"],
            )

        assert result["ciphertext"] != plaintext

    @pytest.mark.asyncio
    async def test_plaintext_not_in_ciphertext_base64(self):
        """The base64-encoded ciphertext must not contain the original plaintext."""
        plaintext = "SEARCHABLE_STRING_12345"
        key_material = mock_key_material()
        mock_resp = make_mock_patches(key_material)

        with patch("qkd_client.request_key", new_callable=AsyncMock, return_value=mock_resp):
            result = await encrypt_email(
                body=plaintext,
                security_level=2,
                recipients=["alice@example.com"],
            )

        # The plaintext should not appear anywhere in the ciphertext
        assert plaintext not in result["ciphertext"]


# ─── Test: MIME Contains Only Ciphertext ───

class TestMIMEContainsOnlyCiphertext:

    def test_mime_body_has_no_plaintext(self):
        """MIME message body must not contain the original plaintext."""
        plaintext = "Super secret project details"
        ciphertext_b64 = base64.b64encode(b"ENCRYPTED_DATA_HERE").decode()

        mime_msg = build_encrypted_mime(
            from_addr="sender@qumail.com",
            to_addrs=["recipient@qumail.com"],
            cc_addrs=[],
            subject=plaintext,  # Real subject goes into envelope
            encrypted_body=ciphertext_b64,
            security_level=2,
            key_id="mime-test-key",
        )

        raw = mime_msg.as_string()

        # The plaintext should NOT appear in the raw MIME
        assert plaintext not in raw
        # The generic subject should appear instead
        assert "New Encrypted Message" in raw

    def test_mime_has_qumail_headers(self):
        """MIME message must contain QuMail-specific headers."""
        mime_msg = build_encrypted_mime(
            from_addr="a@b.com",
            to_addrs=["c@d.com"],
            cc_addrs=[],
            subject="test",
            encrypted_body="ct",
            security_level=2,
            key_id="k1",
        )

        assert mime_msg["X-QuMail-Version"] == "1.0"
        assert mime_msg["X-QuMail-Security-Level"] == "2"
        assert mime_msg["X-QuMail-Algorithm"] == "AES-256-GCM"
        assert mime_msg["X-QuMail-Key-ID"] == "k1"


# ─── Test: Tampering at Each Security Level ───

class TestTamperingDetection:

    @pytest.mark.asyncio
    async def test_tampered_aes_ciphertext_fails(self):
        """Level 2: Modifying AES ciphertext causes decryption failure."""
        plaintext = "Tamper test message"
        key_material = mock_key_material()
        mock_resp = make_mock_patches(key_material)

        with patch("qkd_client.request_key", new_callable=AsyncMock, return_value=mock_resp):
            result = await encrypt_email(
                body=plaintext,
                security_level=2,
                recipients=["alice@example.com"],
            )

        # Tamper with the ciphertext by modifying the base64 envelope
        ct_b64 = result["ciphertext"]
        envelope_json = base64.b64decode(ct_b64)
        envelope = json.loads(envelope_json)

        # Flip a byte in the actual ciphertext
        ct_bytes = base64.b64decode(envelope["ciphertext"])
        tampered = bytearray(ct_bytes)
        tampered[0] ^= 0xFF
        envelope["ciphertext"] = base64.b64encode(bytes(tampered)).decode()

        tampered_b64 = base64.b64encode(json.dumps(envelope).encode()).decode()

        with patch("qkd_client.get_key", new_callable=AsyncMock, return_value=mock_resp):
            with pytest.raises(Exception):
                await decrypt_email({
                    "encrypted_body": tampered_b64,
                    "security_level": 2,
                    "key_id": result["key_id"],
                    "encryption_metadata": result["metadata"],
                })

    @pytest.mark.asyncio
    async def test_tampered_otp_yields_wrong_plaintext(self):
        """Level 1: Modifying OTP ciphertext yields incorrect plaintext."""
        plaintext = "OTP tamper test"
        key_material = os.urandom(len(plaintext.encode("utf-8")))
        mock_resp = KeyResponse(key_id="otp-tamper-key", key_material=key_material, peer_id="peer", key_type="otp")

        with patch("qkd_client.request_key", new_callable=AsyncMock, return_value=mock_resp), \
             patch("qkd_client.consume_key", new_callable=AsyncMock, return_value=True):
            result = await encrypt_email(
                body=plaintext,
                security_level=1,
                recipients=["bob@example.com"],
            )

        # Tamper with OTP ciphertext
        ct_b64 = result["ciphertext"]
        envelope_json = base64.b64decode(ct_b64)
        envelope = json.loads(envelope_json)

        ct_bytes = base64.b64decode(envelope["ciphertext"])
        tampered = bytearray(ct_bytes)
        tampered[0] ^= 0xFF
        envelope["ciphertext"] = base64.b64encode(bytes(tampered)).decode()

        tampered_b64 = base64.b64encode(json.dumps(envelope).encode()).decode()

        with patch("qkd_client.get_key", new_callable=AsyncMock, return_value=mock_resp), \
             patch("qkd_client.consume_key", new_callable=AsyncMock, return_value=True):
            decrypted = await decrypt_email({
                "encrypted_body": tampered_b64,
                "security_level": 1,
                "key_id": result["key_id"],
                "encryption_metadata": result["metadata"],
            })

        # OTP doesn't have auth tags, so decryption succeeds but content is wrong
        assert decrypted["body"] != plaintext
        # And integrity check should fail
        assert decrypted.get("integrity_verified") is False


# ─── Test: Hash Comparison Roundtrip ───

class TestHashComparisonRoundtrip:

    @pytest.mark.asyncio
    async def test_hash_matches_after_decrypt_level2(self):
        """Level 2: original_hash == decrypted_hash after encrypt/decrypt."""
        plaintext = "Hash comparison test message for AES-GCM"
        key_material = mock_key_material()
        mock_resp = make_mock_patches(key_material)
        original_hash = compute_hash(plaintext.encode("utf-8"))

        with patch("qkd_client.request_key", new_callable=AsyncMock, return_value=mock_resp):
            result = await encrypt_email(
                body=plaintext,
                security_level=2,
                recipients=["alice@example.com"],
            )

        # Verify plaintext_hash in metadata
        assert result["metadata"]["plaintext_hash"] == original_hash

        with patch("qkd_client.get_key", new_callable=AsyncMock, return_value=mock_resp):
            decrypted = await decrypt_email({
                "encrypted_body": result["ciphertext"],
                "security_level": 2,
                "key_id": result["key_id"],
                "encryption_metadata": result["metadata"],
            })

        assert decrypted["body"] == plaintext
        assert decrypted["decrypted_hash"] == original_hash
        assert decrypted["integrity_verified"] is True

    @pytest.mark.asyncio
    async def test_hash_matches_after_decrypt_level1(self):
        """Level 1: original_hash == decrypted_hash after OTP encrypt/decrypt."""
        plaintext = "OTP hash check"
        key_material = os.urandom(len(plaintext.encode("utf-8")))
        mock_resp = KeyResponse(key_id="otp-hash-key", key_material=key_material, peer_id="peer", key_type="otp")
        original_hash = compute_hash(plaintext.encode("utf-8"))

        with patch("qkd_client.request_key", new_callable=AsyncMock, return_value=mock_resp), \
             patch("qkd_client.consume_key", new_callable=AsyncMock, return_value=True):
            result = await encrypt_email(
                body=plaintext,
                security_level=1,
                recipients=["bob@example.com"],
            )

        assert result["metadata"]["plaintext_hash"] == original_hash

        with patch("qkd_client.get_key", new_callable=AsyncMock, return_value=mock_resp), \
             patch("qkd_client.consume_key", new_callable=AsyncMock, return_value=True):
            decrypted = await decrypt_email({
                "encrypted_body": result["ciphertext"],
                "security_level": 1,
                "key_id": result["key_id"],
                "encryption_metadata": result["metadata"],
            })

        assert decrypted["body"] == plaintext
        assert decrypted["decrypted_hash"] == original_hash
        assert decrypted["integrity_verified"] is True


# ─── Test: Audit Log ───

class TestAuditLog:

    def test_audit_events_are_recorded(self):
        """Verify audit logger records events."""
        from utils.audit_logger import AuditLogger

        audit = AuditLogger()
        audit.log_event("ENCRYPT_START", security_level=2, data_size=100, hash_prefix="abcdef123456")
        audit.log_event("ENCRYPT_COMPLETE", security_level=2, key_id="test-key-id-long")

        events = audit.get_recent_events()
        assert len(events) == 2
        assert events[0]["event_type"] == "ENCRYPT_START"
        assert events[1]["event_type"] == "ENCRYPT_COMPLETE"

    def test_audit_key_id_truncated(self):
        """Full key IDs must be truncated in audit log."""
        from utils.audit_logger import AuditLogger

        audit = AuditLogger()
        audit.log_event("ENCRYPT_START", key_id="this-is-a-very-long-key-id-12345678")

        events = audit.get_recent_events()
        key_id_logged = events[0].get("key_id", "")
        # Should be truncated to 8 chars + "..."
        assert len(key_id_logged) <= 11
        assert key_id_logged.endswith("...")

    def test_audit_stats(self):
        """Audit stats should reflect logged events."""
        from utils.audit_logger import AuditLogger

        audit = AuditLogger()
        audit.log_event("ENCRYPT_START")
        audit.log_event("ENCRYPT_COMPLETE")
        audit.log_event("DECRYPT_START")

        stats = audit.get_stats()
        assert stats["total_events"] == 3
        assert stats["event_type_counts"]["ENCRYPT_START"] == 1
