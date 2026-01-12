import hmac
import hashlib
from typing import Tuple


def otp_encrypt(plaintext: bytes, key: bytes) -> bytes:
    if len(key) < len(plaintext):
        raise ValueError(
            f"OTP key length ({len(key)}) must be >= plaintext length ({len(plaintext)}). "
            "This is a fundamental requirement of One-Time Pad encryption."
        )
    
    if len(key) > len(plaintext):
        key = key[:len(plaintext)]
    
    ciphertext = bytes(p ^ k for p, k in zip(plaintext, key))
    
    return ciphertext


def otp_decrypt(ciphertext: bytes, key: bytes) -> bytes:
    return otp_encrypt(ciphertext, key)


def otp_encrypt_with_mac(
    plaintext: bytes,
    encryption_key: bytes,
    mac_key: bytes,
) -> Tuple[bytes, bytes]:
    if len(mac_key) < 32:
        raise ValueError("MAC key must be at least 32 bytes")
    
    ciphertext = otp_encrypt(plaintext, encryption_key)
    
    mac = hmac.new(mac_key, ciphertext, hashlib.sha256).digest()
    
    return ciphertext, mac


def otp_decrypt_with_mac(
    ciphertext: bytes,
    mac: bytes,
    encryption_key: bytes,
    mac_key: bytes,
) -> bytes:
    expected_mac = hmac.new(mac_key, ciphertext, hashlib.sha256).digest()
    
    if not hmac.compare_digest(mac, expected_mac):
        raise ValueError("MAC verification failed - message may have been tampered with")
    
    return otp_decrypt(ciphertext, encryption_key)


def verify_otp_security(key: bytes, plaintext_length: int) -> dict:
    issues = []
    
    if len(key) < plaintext_length:
        issues.append(f"Key too short: {len(key)} < {plaintext_length}")
    
    if len(set(key)) < min(len(key) // 4, 64):
        issues.append("Key appears to have low entropy (many repeated bytes)")
    
    byte_counts = {}
    for b in key:
        byte_counts[b] = byte_counts.get(b, 0) + 1
    
    max_count = max(byte_counts.values()) if byte_counts else 0
    if max_count > len(key) * 0.1:
        issues.append(f"Key has suspicious byte distribution (max: {max_count}/{len(key)})")
    
    return {
        "valid": len(issues) == 0,
        "key_length": len(key),
        "plaintext_length": plaintext_length,
        "issues": issues,
    }
