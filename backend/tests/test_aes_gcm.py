import os
import pytest
from crypto_engine.aes_gcm import (
    aes_encrypt,
    aes_decrypt,
    aes_encrypt_combined,
    aes_decrypt_combined,
    generate_aes_key,
    KEY_SIZE,
    NONCE_SIZE,
    TAG_SIZE,
)


class TestAESEncryption:
    
    def test_encrypt_decrypt_roundtrip(self, sample_plaintext, aes_key):
        ciphertext, nonce, tag = aes_encrypt(sample_plaintext, aes_key)
        decrypted = aes_decrypt(ciphertext, aes_key, nonce, tag)
        assert decrypted == sample_plaintext
    
    def test_ciphertext_different_from_plaintext(self, sample_plaintext, aes_key):
        ciphertext, nonce, tag = aes_encrypt(sample_plaintext, aes_key)
        assert ciphertext != sample_plaintext
    
    def test_nonce_is_correct_size(self, sample_plaintext, aes_key):
        ciphertext, nonce, tag = aes_encrypt(sample_plaintext, aes_key)
        assert len(nonce) == NONCE_SIZE
    
    def test_tag_is_correct_size(self, sample_plaintext, aes_key):
        ciphertext, nonce, tag = aes_encrypt(sample_plaintext, aes_key)
        assert len(tag) == TAG_SIZE
    
    def test_invalid_key_size_raises_error(self, sample_plaintext):
        invalid_key = os.urandom(16)
        with pytest.raises(ValueError, match="Key must be"):
            aes_encrypt(sample_plaintext, invalid_key)
    
    def test_invalid_nonce_size_raises_error(self, sample_plaintext, aes_key):
        ciphertext, nonce, tag = aes_encrypt(sample_plaintext, aes_key)
        invalid_nonce = os.urandom(8)
        with pytest.raises(ValueError, match="Nonce must be"):
            aes_decrypt(ciphertext, aes_key, invalid_nonce, tag)
    
    def test_invalid_tag_size_raises_error(self, sample_plaintext, aes_key):
        ciphertext, nonce, tag = aes_encrypt(sample_plaintext, aes_key)
        invalid_tag = os.urandom(8)
        with pytest.raises(ValueError, match="Tag must be"):
            aes_decrypt(ciphertext, aes_key, nonce, invalid_tag)
    
    def test_tampered_ciphertext_fails_decryption(self, sample_plaintext, aes_key):
        ciphertext, nonce, tag = aes_encrypt(sample_plaintext, aes_key)
        tampered = bytes([(b + 1) % 256 for b in ciphertext])
        with pytest.raises(Exception):
            aes_decrypt(tampered, aes_key, nonce, tag)
    
    def test_tampered_tag_fails_decryption(self, sample_plaintext, aes_key):
        ciphertext, nonce, tag = aes_encrypt(sample_plaintext, aes_key)
        tampered_tag = bytes([(b + 1) % 256 for b in tag])
        with pytest.raises(Exception):
            aes_decrypt(ciphertext, aes_key, nonce, tampered_tag)
    
    def test_wrong_key_fails_decryption(self, sample_plaintext, aes_key):
        ciphertext, nonce, tag = aes_encrypt(sample_plaintext, aes_key)
        wrong_key = os.urandom(KEY_SIZE)
        with pytest.raises(Exception):
            aes_decrypt(ciphertext, wrong_key, nonce, tag)
    
    def test_unique_nonces_per_encryption(self, sample_plaintext, aes_key):
        nonces = set()
        for _ in range(100):
            _, nonce, _ = aes_encrypt(sample_plaintext, aes_key)
            nonces.add(nonce)
        assert len(nonces) == 100
    
    def test_associated_data_authentication(self, sample_plaintext, aes_key):
        aad = b"authenticated but not encrypted"
        ciphertext, nonce, tag = aes_encrypt(sample_plaintext, aes_key, aad)
        decrypted = aes_decrypt(ciphertext, aes_key, nonce, tag, aad)
        assert decrypted == sample_plaintext
    
    def test_wrong_associated_data_fails(self, sample_plaintext, aes_key):
        aad = b"correct aad"
        ciphertext, nonce, tag = aes_encrypt(sample_plaintext, aes_key, aad)
        wrong_aad = b"wrong aad"
        with pytest.raises(Exception):
            aes_decrypt(ciphertext, aes_key, nonce, tag, wrong_aad)
    
    def test_large_plaintext(self, large_plaintext, aes_key):
        ciphertext, nonce, tag = aes_encrypt(large_plaintext, aes_key)
        decrypted = aes_decrypt(ciphertext, aes_key, nonce, tag)
        assert decrypted == large_plaintext
    
    def test_empty_plaintext(self, aes_key):
        plaintext = b""
        ciphertext, nonce, tag = aes_encrypt(plaintext, aes_key)
        decrypted = aes_decrypt(ciphertext, aes_key, nonce, tag)
        assert decrypted == plaintext


class TestAESCombined:
    
    def test_combined_encrypt_decrypt_roundtrip(self, sample_plaintext, aes_key):
        combined = aes_encrypt_combined(sample_plaintext, aes_key)
        decrypted = aes_decrypt_combined(combined, aes_key)
        assert decrypted == sample_plaintext
    
    def test_combined_contains_nonce(self, sample_plaintext, aes_key):
        combined = aes_encrypt_combined(sample_plaintext, aes_key)
        assert len(combined) >= NONCE_SIZE + TAG_SIZE
    
    def test_combined_too_short_raises_error(self, aes_key):
        short_data = os.urandom(10)
        with pytest.raises(ValueError, match="too short"):
            aes_decrypt_combined(short_data, aes_key)
    
    def test_combined_with_associated_data(self, sample_plaintext, aes_key):
        aad = b"test aad"
        combined = aes_encrypt_combined(sample_plaintext, aes_key, aad)
        decrypted = aes_decrypt_combined(combined, aes_key, aad)
        assert decrypted == sample_plaintext


class TestKeyGeneration:
    
    def test_generate_aes_key_correct_size(self):
        key = generate_aes_key()
        assert len(key) == KEY_SIZE
    
    def test_generate_aes_key_is_random(self):
        keys = [generate_aes_key() for _ in range(100)]
        unique_keys = set(keys)
        assert len(unique_keys) == 100
    
    def test_generated_key_works_for_encryption(self, sample_plaintext):
        key = generate_aes_key()
        ciphertext, nonce, tag = aes_encrypt(sample_plaintext, key)
        decrypted = aes_decrypt(ciphertext, key, nonce, tag)
        assert decrypted == sample_plaintext
