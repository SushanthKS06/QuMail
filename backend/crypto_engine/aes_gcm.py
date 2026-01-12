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
    nonce = os.urandom(NONCE_SIZE)
    aesgcm = AESGCM(key)
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext, associated_data)
    
    return nonce + ciphertext_with_tag


def aes_decrypt_combined(
    combined: bytes,
    key: bytes,
    associated_data: bytes = b"",
) -> bytes:
    if len(combined) < NONCE_SIZE + TAG_SIZE:
        raise ValueError("Combined data too short")
    
    nonce = combined[:NONCE_SIZE]
    ciphertext_with_tag = combined[NONCE_SIZE:]
    
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, associated_data)
    
    return plaintext


def generate_aes_key() -> bytes:
    return os.urandom(KEY_SIZE)
