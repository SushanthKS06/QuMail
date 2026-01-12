"""
Secure Random Generation

Provides cryptographically secure random number generation
for nonces, salts, and other security-critical random values.
"""

import os
import secrets
from typing import Optional


def secure_random_bytes(length: int) -> bytes:
    """
    Generate cryptographically secure random bytes.
    
    Uses os.urandom() which sources from the OS CSPRNG.
    
    Args:
        length: Number of random bytes to generate
    
    Returns:
        Cryptographically secure random bytes
    """
    if length <= 0:
        raise ValueError("Length must be positive")
    
    return os.urandom(length)


def secure_random_hex(length: int) -> str:
    """
    Generate a cryptographically secure random hex string.
    
    Args:
        length: Number of hex characters (output will be this length)
    
    Returns:
        Random hex string
    """
    byte_length = (length + 1) // 2
    return secrets.token_hex(byte_length)[:length]


def secure_random_urlsafe(length: int) -> str:
    """
    Generate a cryptographically secure URL-safe random string.
    
    Args:
        length: Approximate length of output
    
    Returns:
        URL-safe random string
    """
    return secrets.token_urlsafe(length)


def secure_compare(a: bytes, b: bytes) -> bool:
    """
    Constant-time comparison of two byte strings.
    
    Prevents timing attacks by ensuring comparison takes
    the same time regardless of where strings differ.
    
    Args:
        a: First byte string
        b: Second byte string
    
    Returns:
        True if strings are equal
    """
    return secrets.compare_digest(a, b)


def generate_nonce(length: int = 12) -> bytes:
    """Generate a random nonce for encryption."""
    return secure_random_bytes(length)


def generate_salt(length: int = 16) -> bytes:
    """Generate a random salt for key derivation."""
    return secure_random_bytes(length)


def generate_key_id() -> str:
    """Generate a unique key identifier."""
    import uuid
    return str(uuid.uuid4())


def zeroize(data: bytearray) -> None:
    """
    Securely overwrite memory with zeros.
    
    Used to clear sensitive data from memory after use.
    Note: This works on mutable bytearrays, not immutable bytes.
    
    Args:
        data: Bytearray to zeroize (modified in place)
    """
    for i in range(len(data)):
        data[i] = 0
