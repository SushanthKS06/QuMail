"""
Test suite for ciphertext tampering detection.

Proves that AES-GCM's authentication mechanisms detect all forms
of ciphertext manipulation, providing verifiable proof of integrity.
"""

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


class TestBitFlipTampering:
    """Test that flipping any bit in ciphertext is detected."""

    def test_single_bit_flip_first_byte(self, sample_plaintext, aes_key):
        ciphertext, nonce, tag = aes_encrypt(sample_plaintext, aes_key)
        tampered = bytearray(ciphertext)
        tampered[0] ^= 0x01
        with pytest.raises(Exception):
            aes_decrypt(bytes(tampered), aes_key, nonce, tag)

    def test_single_bit_flip_last_byte(self, sample_plaintext, aes_key):
        ciphertext, nonce, tag = aes_encrypt(sample_plaintext, aes_key)
        tampered = bytearray(ciphertext)
        tampered[-1] ^= 0x01
        with pytest.raises(Exception):
            aes_decrypt(bytes(tampered), aes_key, nonce, tag)

    def test_single_bit_flip_middle_byte(self, sample_plaintext, aes_key):
        ciphertext, nonce, tag = aes_encrypt(sample_plaintext, aes_key)
        mid = len(ciphertext) // 2
        tampered = bytearray(ciphertext)
        tampered[mid] ^= 0x80
        with pytest.raises(Exception):
            aes_decrypt(bytes(tampered), aes_key, nonce, tag)

    def test_multiple_bit_flips(self, sample_plaintext, aes_key):
        ciphertext, nonce, tag = aes_encrypt(sample_plaintext, aes_key)
        tampered = bytearray(ciphertext)
        for i in range(0, len(tampered), max(1, len(tampered) // 5)):
            tampered[i] ^= 0xFF
        with pytest.raises(Exception):
            aes_decrypt(bytes(tampered), aes_key, nonce, tag)


class TestNonceTampering:
    """Test that nonce modification is detected."""

    def test_nonce_first_byte_flip(self, sample_plaintext, aes_key):
        ciphertext, nonce, tag = aes_encrypt(sample_plaintext, aes_key)
        tampered_nonce = bytearray(nonce)
        tampered_nonce[0] ^= 0x01
        with pytest.raises(Exception):
            aes_decrypt(ciphertext, aes_key, bytes(tampered_nonce), tag)

    def test_nonce_all_zeros(self, sample_plaintext, aes_key):
        ciphertext, nonce, tag = aes_encrypt(sample_plaintext, aes_key)
        with pytest.raises(Exception):
            aes_decrypt(ciphertext, aes_key, b"\x00" * NONCE_SIZE, tag)

    def test_nonce_replaced(self, sample_plaintext, aes_key):
        ciphertext, nonce, tag = aes_encrypt(sample_plaintext, aes_key)
        fake_nonce = os.urandom(NONCE_SIZE)
        with pytest.raises(Exception):
            aes_decrypt(ciphertext, aes_key, fake_nonce, tag)


class TestTagTampering:
    """Test that authentication tag modification is detected."""

    def test_tag_single_bit_flip(self, sample_plaintext, aes_key):
        ciphertext, nonce, tag = aes_encrypt(sample_plaintext, aes_key)
        tampered_tag = bytearray(tag)
        tampered_tag[0] ^= 0x01
        with pytest.raises(Exception):
            aes_decrypt(ciphertext, aes_key, nonce, bytes(tampered_tag))

    def test_tag_all_zeros(self, sample_plaintext, aes_key):
        ciphertext, nonce, tag = aes_encrypt(sample_plaintext, aes_key)
        with pytest.raises(Exception):
            aes_decrypt(ciphertext, aes_key, nonce, b"\x00" * TAG_SIZE)

    def test_tag_replaced_with_random(self, sample_plaintext, aes_key):
        ciphertext, nonce, tag = aes_encrypt(sample_plaintext, aes_key)
        with pytest.raises(Exception):
            aes_decrypt(ciphertext, aes_key, nonce, os.urandom(TAG_SIZE))


class TestTruncationTampering:
    """Test that truncated ciphertext is rejected."""

    def test_truncated_ciphertext(self, sample_plaintext, aes_key):
        ciphertext, nonce, tag = aes_encrypt(sample_plaintext, aes_key)
        truncated = ciphertext[:len(ciphertext) // 2]
        with pytest.raises(Exception):
            aes_decrypt(truncated, aes_key, nonce, tag)

    def test_empty_ciphertext(self, aes_key):
        _, nonce, tag = aes_encrypt(b"test", aes_key)
        with pytest.raises(Exception):
            aes_decrypt(b"", aes_key, nonce, tag)

    def test_extended_ciphertext(self, sample_plaintext, aes_key):
        ciphertext, nonce, tag = aes_encrypt(sample_plaintext, aes_key)
        extended = ciphertext + b"\x00" * 16
        with pytest.raises(Exception):
            aes_decrypt(extended, aes_key, nonce, tag)


class TestReplayAttack:
    """Test that ciphertext from one key cannot be decrypted with another."""

    def test_replay_different_key(self, sample_plaintext):
        key1 = generate_aes_key()
        key2 = generate_aes_key()

        ciphertext, nonce, tag = aes_encrypt(sample_plaintext, key1)

        with pytest.raises(Exception):
            aes_decrypt(ciphertext, key2, nonce, tag)

    def test_replay_swapped_nonce_tag(self, sample_plaintext, aes_key):
        """Encrypt two messages, try decrypting one with the other's nonce/tag."""
        msg1 = b"Message number one"
        msg2 = b"Message number two"

        ct1, nonce1, tag1 = aes_encrypt(msg1, aes_key)
        ct2, nonce2, tag2 = aes_encrypt(msg2, aes_key)

        # Try ct1 with nonce2/tag2
        with pytest.raises(Exception):
            aes_decrypt(ct1, aes_key, nonce2, tag2)


class TestCombinedTampering:
    """Test tampering detection in combined mode (nonce||ciphertext||tag)."""

    def test_combined_bit_flip(self, sample_plaintext, aes_key):
        combined = aes_encrypt_combined(sample_plaintext, aes_key)
        tampered = bytearray(combined)
        tampered[NONCE_SIZE + 1] ^= 0x01
        with pytest.raises(Exception):
            aes_decrypt_combined(bytes(tampered), aes_key)

    def test_combined_truncated(self, sample_plaintext, aes_key):
        combined = aes_encrypt_combined(sample_plaintext, aes_key)
        with pytest.raises(Exception):
            aes_decrypt_combined(combined[:NONCE_SIZE + 5], aes_key)
