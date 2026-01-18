import os
import pytest
from crypto_engine.secure_random import secure_random_bytes


class TestSecureRandom:
    
    def test_secure_random_bytes_returns_bytes(self):
        result = secure_random_bytes(32)
        assert isinstance(result, bytes)
    
    def test_secure_random_bytes_correct_length(self):
        for length in [1, 16, 32, 64, 128, 256, 1024]:
            result = secure_random_bytes(length)
            assert len(result) == length
    
    def test_secure_random_bytes_zero_length_raises_error(self):
        with pytest.raises(ValueError):
            secure_random_bytes(0)
    
    def test_secure_random_bytes_are_random(self):
        results = [secure_random_bytes(32) for _ in range(100)]
        unique_results = set(results)
        assert len(unique_results) == 100
    
    def test_secure_random_bytes_high_entropy(self):
        result = secure_random_bytes(256)
        unique_bytes = len(set(result))
        assert unique_bytes >= 200
    
    def test_secure_random_bytes_large_size(self):
        result = secure_random_bytes(1024 * 1024)
        assert len(result) == 1024 * 1024
    
    def test_secure_random_bytes_distribution(self):
        result = secure_random_bytes(10000)
        byte_counts = {}
        for b in result:
            byte_counts[b] = byte_counts.get(b, 0) + 1
        
        min_count = min(byte_counts.values())
        max_count = max(byte_counts.values())
        assert max_count < min_count * 5


class TestSecureRandomIntegration:
    
    def test_random_bytes_usable_as_key(self):
        from crypto_engine.aes_gcm import aes_encrypt, aes_decrypt
        
        key = secure_random_bytes(32)
        plaintext = b"test message"
        ciphertext, nonce, tag = aes_encrypt(plaintext, key)
        decrypted = aes_decrypt(ciphertext, key, nonce, tag)
        assert decrypted == plaintext
    
    def test_random_bytes_usable_as_otp_key(self):
        from crypto_engine.otp import otp_encrypt, otp_decrypt
        
        plaintext = b"test message for OTP"
        key = secure_random_bytes(len(plaintext))
        ciphertext = otp_encrypt(plaintext, key)
        decrypted = otp_decrypt(ciphertext, key)
        assert decrypted == plaintext
