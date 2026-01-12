import os
import secrets
from typing import Optional


def secure_random_bytes(length: int) -> bytes:
    if length <= 0:
        raise ValueError("Length must be positive")
    
    return os.urandom(length)


def secure_random_hex(length: int) -> str:
    byte_length = (length + 1) // 2
    return secrets.token_hex(byte_length)[:length]


def secure_random_urlsafe(length: int) -> str:
    return secrets.token_urlsafe(length)


def secure_compare(a: bytes, b: bytes) -> bool:
    return secrets.compare_digest(a, b)


def generate_nonce(length: int = 12) -> bytes:
    return secure_random_bytes(length)


def generate_salt(length: int = 16) -> bytes:
    return secure_random_bytes(length)


def generate_key_id() -> str:
    import uuid
    return str(uuid.uuid4())


def zeroize(data: bytearray) -> None:
    for i in range(len(data)):
        data[i] = 0
