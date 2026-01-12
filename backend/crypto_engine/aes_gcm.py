"""
AES-256-GCM Implementation

Level 2 Security: Quantum-Aided symmetric encryption.

Uses AES-256 in Galois/Counter Mode (GCM) which provides:
- Confidentiality (encryption)
- Integrity (authentication tag)
- Authentication (AEAD)

The key is derived from QKD material, providing quantum-level
randomness for key generation.
"""

import os
from typing import Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


NONCE_SIZE = 12
TAG_SIZE = 16
KEY_SIZE = 32


def aes_encrypt(
    plaintext: bytes,
    key: bytes,
    associated_data: bytes = b"",
) -> Tuple[bytes, bytes, bytes]:
    """
    Encrypt data using AES-256-GCM.
    
    Args:
        plaintext: Data to encrypt
        key: 256-bit (32 byte) encryption key
        associated_data: Optional additional authenticated data
    
    Returns:
        Tuple of (ciphertext, nonce, tag)
        - ciphertext: The encrypted data (same length as plaintext)
        - nonce: 12-byte random nonce (must be stored for decryption)
        - tag: 16-byte authentication tag
    """
    if len(key) != KEY_SIZE:
        raise ValueError(f"Key must be {KEY_SIZE} bytes, got {len(key)}")
    
    nonce = os.urandom(NONCE_SIZE)
    
    aesgcm = AESGCM(key)
    
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext, associated_data)
    
    ciphertext = ciphertext_with_tag[:-TAG_SIZE]
    tag = ciphertext_with_tag[-TAG_SIZE:]
    
    return ciphertext, nonce, tag


def aes_decrypt(
    ciphertext: bytes,
    key: bytes,
    nonce: bytes,
    tag: bytes,
    associated_data: bytes = b"",
) -> bytes:
    """
    Decrypt data using AES-256-GCM.
    
    Args:
        ciphertext: Encrypted data
        key: 256-bit encryption key (same as used for encryption)
        nonce: 12-byte nonce used during encryption
        tag: 16-byte authentication tag
        associated_data: Optional additional authenticated data
    
    Returns:
        Decrypted plaintext
    
    Raises:
        cryptography.exceptions.InvalidTag: If authentication fails
    """
    if len(key) != KEY_SIZE:
        raise ValueError(f"Key must be {KEY_SIZE} bytes, got {len(key)}")
    
    if len(nonce) != NONCE_SIZE:
        raise ValueError(f"Nonce must be {NONCE_SIZE} bytes, got {len(nonce)}")
    
    if len(tag) != TAG_SIZE:
        raise ValueError(f"Tag must be {TAG_SIZE} bytes, got {len(tag)}")
    
    aesgcm = AESGCM(key)
    
    ciphertext_with_tag = ciphertext + tag
    
    plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, associated_data)
    
    return plaintext


def aes_encrypt_combined(
    plaintext: bytes,
    key: bytes,
    associated_data: bytes = b"",
) -> bytes:
    """
    Encrypt and return combined output (nonce + ciphertext + tag).
    
    Convenience function for when storing as a single blob.
    
    Args:
        plaintext: Data to encrypt
        key: 256-bit encryption key
        associated_data: Optional AAD
    
    Returns:
        Combined bytes: nonce (12) + ciphertext + tag (16)
    """
    nonce = os.urandom(NONCE_SIZE)
    aesgcm = AESGCM(key)
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext, associated_data)
    
    return nonce + ciphertext_with_tag


def aes_decrypt_combined(
    combined: bytes,
    key: bytes,
    associated_data: bytes = b"",
) -> bytes:
    """
    Decrypt combined output (nonce + ciphertext + tag).
    
    Args:
        combined: Combined bytes from aes_encrypt_combined
        key: 256-bit encryption key
        associated_data: Optional AAD
    
    Returns:
        Decrypted plaintext
    """
    if len(combined) < NONCE_SIZE + TAG_SIZE:
        raise ValueError("Combined data too short")
    
    nonce = combined[:NONCE_SIZE]
    ciphertext_with_tag = combined[NONCE_SIZE:]
    
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, associated_data)
    
    return plaintext


def generate_aes_key() -> bytes:
    """Generate a random 256-bit AES key."""
    return os.urandom(KEY_SIZE)
