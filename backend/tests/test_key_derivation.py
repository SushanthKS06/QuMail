import os
import pytest
from crypto_engine.key_derivation import (
    derive_key,
    derive_multiple_keys,
    derive_email_keys,
)


class TestKeyDerivation:
    
    def test_derive_key_returns_bytes(self):
        ikm = os.urandom(32)
        context = b"test-context"
        result = derive_key(ikm, context, 32)
        assert isinstance(result, bytes)
    
    def test_derive_key_correct_length(self):
        ikm = os.urandom(32)
        context = b"test-context"
        for length in [16, 32, 64, 128]:
            result = derive_key(ikm, context, length)
            assert len(result) == length
    
    def test_derive_key_deterministic(self):
        ikm = os.urandom(32)
        context = b"test-context"
        result1 = derive_key(ikm, context, 32)
        result2 = derive_key(ikm, context, 32)
        assert result1 == result2
    
    def test_derive_key_different_context_different_output(self):
        ikm = os.urandom(32)
        result1 = derive_key(ikm, b"context-1", 32)
        result2 = derive_key(ikm, b"context-2", 32)
        assert result1 != result2
    
    def test_derive_key_different_ikm_different_output(self):
        context = b"test-context"
        result1 = derive_key(os.urandom(32), context, 32)
        result2 = derive_key(os.urandom(32), context, 32)
        assert result1 != result2
    
    def test_derive_key_with_salt(self):
        ikm = os.urandom(32)
        context = b"test-context"
        salt = os.urandom(16)
        result_with_salt = derive_key(ikm, context, 32, salt)
        result_without_salt = derive_key(ikm, context, 32)
        assert result_with_salt != result_without_salt
    
    def test_derive_key_empty_ikm_raises_error(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            derive_key(b"", b"context", 32)
    
    def test_derive_key_zero_length_raises_error(self):
        ikm = os.urandom(32)
        with pytest.raises(ValueError, match="Invalid key length"):
            derive_key(ikm, b"context", 0)
    
    def test_derive_key_negative_length_raises_error(self):
        ikm = os.urandom(32)
        with pytest.raises(ValueError, match="Invalid key length"):
            derive_key(ikm, b"context", -1)
    
    def test_derive_key_excessive_length_raises_error(self):
        ikm = os.urandom(32)
        with pytest.raises(ValueError, match="Invalid key length"):
            derive_key(ikm, b"context", 255 * 32 + 1)


class TestDeriveMultipleKeys:
    
    def test_derive_multiple_keys_returns_list(self):
        ikm = os.urandom(32)
        contexts = [(b"key1", 32), (b"key2", 16)]
        result = derive_multiple_keys(ikm, contexts)
        assert isinstance(result, list)
        assert len(result) == 2
    
    def test_derive_multiple_keys_correct_lengths(self):
        ikm = os.urandom(32)
        contexts = [(b"key1", 16), (b"key2", 32), (b"key3", 64)]
        result = derive_multiple_keys(ikm, contexts)
        assert len(result[0]) == 16
        assert len(result[1]) == 32
        assert len(result[2]) == 64
    
    def test_derive_multiple_keys_all_different(self):
        ikm = os.urandom(32)
        contexts = [(b"key1", 32), (b"key2", 32), (b"key3", 32)]
        result = derive_multiple_keys(ikm, contexts)
        assert result[0] != result[1]
        assert result[1] != result[2]
        assert result[0] != result[2]


class TestDeriveEmailKeys:
    
    def test_derive_email_keys_returns_dict(self):
        qkd_key = os.urandom(32)
        email_id = "test-email-12345"
        result = derive_email_keys(qkd_key, email_id)
        assert isinstance(result, dict)
    
    def test_derive_email_keys_contains_required_keys(self):
        qkd_key = os.urandom(32)
        email_id = "test-email-12345"
        result = derive_email_keys(qkd_key, email_id)
        assert "encryption_key" in result
        assert "mac_key" in result
        assert "iv_seed" in result
    
    def test_derive_email_keys_correct_sizes(self):
        qkd_key = os.urandom(32)
        email_id = "test-email-12345"
        result = derive_email_keys(qkd_key, email_id)
        assert len(result["encryption_key"]) == 32
        assert len(result["mac_key"]) == 32
        assert len(result["iv_seed"]) == 16
    
    def test_derive_email_keys_deterministic(self):
        qkd_key = os.urandom(32)
        email_id = "test-email-12345"
        result1 = derive_email_keys(qkd_key, email_id)
        result2 = derive_email_keys(qkd_key, email_id)
        assert result1 == result2
    
    def test_derive_email_keys_different_emails_different_keys(self):
        qkd_key = os.urandom(32)
        result1 = derive_email_keys(qkd_key, "email-1")
        result2 = derive_email_keys(qkd_key, "email-2")
        assert result1["encryption_key"] != result2["encryption_key"]
    
    def test_derive_email_keys_all_subkeys_different(self):
        qkd_key = os.urandom(32)
        email_id = "test-email-12345"
        result = derive_email_keys(qkd_key, email_id)
        assert result["encryption_key"] != result["mac_key"]
