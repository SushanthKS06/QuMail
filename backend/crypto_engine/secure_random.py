import logging
import os
import secrets
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

_use_quantum_sim = True

try:
    from .quantum_sim import (
        generate_quantum_bytes,
        generate_quantum_key,
        get_entropy_stats,
        health_check as entropy_health_check,
        force_reseed,
    )
    logger.info("Quantum-grade entropy module loaded")
except ImportError as e:
    logger.warning("Quantum sim not available, falling back to os.urandom: %s", e)
    _use_quantum_sim = False


def secure_random_bytes(length: int) -> bytes:
    if length <= 0:
        raise ValueError("Length must be positive")
    
    if _use_quantum_sim:
        return generate_quantum_bytes(length)
    
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


def generate_encryption_key(size: int = 32) -> Tuple[bytes, str]:
    if _use_quantum_sim:
        return generate_quantum_key(size)
    
    key_material = os.urandom(size)
    key_id = generate_key_id()
    return key_material, key_id


def get_random_stats() -> dict:
    if _use_quantum_sim:
        return get_entropy_stats()
    
    return {
        "source": "os.urandom",
        "quantum_grade": False,
    }


def check_entropy_health() -> bool:
    if _use_quantum_sim:
        return entropy_health_check()
    return True


def request_reseed() -> None:
    if _use_quantum_sim:
        force_reseed()

