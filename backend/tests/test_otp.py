import pytest
from crypto_engine.otp import (
    otp_encrypt,
    otp_decrypt,
    otp_encrypt_with_mac,
    otp_decrypt_with_mac,
    verify_otp_security,
)


class TestOTPEncryption:
    
    def test_encrypt_decrypt_roundtrip(self, sample_plaintext, otp_key):
        ciphertext = otp_encrypt(sample_plaintext, otp_key)
        decrypted = otp_decrypt(ciphertext, otp_key)
        assert decrypted == sample_plaintext
    
    def test_ciphertext_different_from_plaintext(self, sample_plaintext, otp_key):
        ciphertext = otp_encrypt(sample_plaintext, otp_key)
        assert ciphertext != sample_plaintext
    
    def test_ciphertext_same_length_as_plaintext(self, sample_plaintext, otp_key):
        ciphertext = otp_encrypt(sample_plaintext, otp_key)
        assert len(ciphertext) == len(sample_plaintext)
    
    def test_key_too_short_raises_error(self, sample_plaintext, short_key):
        with pytest.raises(ValueError, match="OTP key length"):
            otp_encrypt(sample_plaintext, short_key)
    
    def test_key_longer_than_plaintext_works(self, sample_plaintext):
        long_key = sample_plaintext + b"extra_key_material"
        ciphertext = otp_encrypt(sample_plaintext, long_key)
        decrypted = otp_decrypt(ciphertext, long_key)
        assert decrypted == sample_plaintext
    
    def test_different_keys_produce_different_ciphertext(self, sample_plaintext):
        key1 = bytes([i % 256 for i in range(len(sample_plaintext))])
        key2 = bytes([(i + 1) % 256 for i in range(len(sample_plaintext))])
        
        cipher1 = otp_encrypt(sample_plaintext, key1)
        cipher2 = otp_encrypt(sample_plaintext, key2)
        
        assert cipher1 != cipher2
    
    def test_wrong_key_produces_wrong_plaintext(self, sample_plaintext, otp_key):
        ciphertext = otp_encrypt(sample_plaintext, otp_key)
        wrong_key = bytes([(b + 1) % 256 for b in otp_key])
        wrong_plaintext = otp_decrypt(ciphertext, wrong_key)
        assert wrong_plaintext != sample_plaintext
    
    def test_empty_plaintext(self):
        plaintext = b""
        key = b""
        ciphertext = otp_encrypt(plaintext, key)
        assert ciphertext == b""
        assert otp_decrypt(ciphertext, key) == plaintext


class TestOTPWithMAC:
    
    def test_encrypt_decrypt_with_mac_roundtrip(self, sample_plaintext, otp_key):
        mac_key = bytes([i % 256 for i in range(32)])
        ciphertext, mac = otp_encrypt_with_mac(sample_plaintext, otp_key, mac_key)
        decrypted = otp_decrypt_with_mac(ciphertext, mac, otp_key, mac_key)
        assert decrypted == sample_plaintext
    
    def test_mac_verification_fails_on_tampered_ciphertext(self, sample_plaintext, otp_key):
        mac_key = bytes([i % 256 for i in range(32)])
        ciphertext, mac = otp_encrypt_with_mac(sample_plaintext, otp_key, mac_key)
        
        tampered = bytes([(b + 1) % 256 for b in ciphertext])
        
        with pytest.raises(ValueError, match="MAC verification failed"):
            otp_decrypt_with_mac(tampered, mac, otp_key, mac_key)
    
    def test_mac_verification_fails_on_wrong_mac(self, sample_plaintext, otp_key):
        mac_key = bytes([i % 256 for i in range(32)])
        ciphertext, mac = otp_encrypt_with_mac(sample_plaintext, otp_key, mac_key)
        
        wrong_mac = bytes([(b + 1) % 256 for b in mac])
        
        with pytest.raises(ValueError, match="MAC verification failed"):
            otp_decrypt_with_mac(ciphertext, wrong_mac, otp_key, mac_key)
    
    def test_mac_key_too_short_raises_error(self, sample_plaintext, otp_key):
        short_mac_key = b"short"
        with pytest.raises(ValueError, match="MAC key must be at least 32 bytes"):
            otp_encrypt_with_mac(sample_plaintext, otp_key, short_mac_key)


class TestOTPSecurityVerification:
    
    def test_valid_key_passes_verification(self, sample_plaintext, otp_key):
        result = verify_otp_security(otp_key, len(sample_plaintext))
        assert result["valid"] is True
        assert len(result["issues"]) == 0
    
    def test_short_key_fails_verification(self, sample_plaintext, short_key):
        result = verify_otp_security(short_key, len(sample_plaintext))
        assert result["valid"] is False
        assert any("too short" in issue.lower() for issue in result["issues"])
    
    def test_low_entropy_key_detected(self, sample_plaintext):
        low_entropy_key = bytes([0] * len(sample_plaintext))
        result = verify_otp_security(low_entropy_key, len(sample_plaintext))
        assert result["valid"] is False
    
    def test_verification_returns_key_stats(self, sample_plaintext, otp_key):
        result = verify_otp_security(otp_key, len(sample_plaintext))
        assert "key_length" in result
        assert "plaintext_length" in result
        assert result["key_length"] == len(otp_key)
        assert result["plaintext_length"] == len(sample_plaintext)
