"""
Key Derivation Functions

Provides HKDF-based key derivation for creating encryption keys
from QKD material.
"""

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


def derive_key(
    input_key_material: bytes,
    context: bytes,
    length: int,
    salt: bytes = b"",
) -> bytes:
    """
    Derive a cryptographic key using HKDF-SHA256.
    
    HKDF (HMAC-based Key Derivation Function) is used to derive
    one or more cryptographically strong keys from input key material.
    
    Args:
        input_key_material: The source key material (e.g., from QKD)
        context: Application-specific context string (info parameter)
        length: Desired output key length in bytes
        salt: Optional salt value (recommended for multi-use keys)
    
    Returns:
        Derived key of the specified length
    """
    if not input_key_material:
        raise ValueError("Input key material cannot be empty")
    
    if length <= 0 or length > 255 * 32:
        raise ValueError(f"Invalid key length: {length}")
    
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=length,
        salt=salt if salt else None,
        info=context,
    )
    
    return hkdf.derive(input_key_material)


def derive_multiple_keys(
    input_key_material: bytes,
    contexts: list[tuple[bytes, int]],
    salt: bytes = b"",
) -> list[bytes]:
    """
    Derive multiple keys with different contexts from the same input.
    
    Args:
        input_key_material: The source key material
        contexts: List of (context, length) tuples
        salt: Optional salt value
    
    Returns:
        List of derived keys in the same order as contexts
    """
    return [
        derive_key(input_key_material, context, length, salt)
        for context, length in contexts
    ]


def derive_email_keys(qkd_key: bytes, email_id: str) -> dict:
    """
    Derive all keys needed for email encryption from a single QKD key.
    
    Args:
        qkd_key: QKD key material
        email_id: Unique email identifier (for domain separation)
    
    Returns:
        Dict with encryption_key, mac_key, and iv_seed
    """
    base_context = f"qumail-email-{email_id}".encode()
    
    encryption_key = derive_key(qkd_key, base_context + b"-enc", 32)
    mac_key = derive_key(qkd_key, base_context + b"-mac", 32)
    iv_seed = derive_key(qkd_key, base_context + b"-iv", 16)
    
    return {
        "encryption_key": encryption_key,
        "mac_key": mac_key,
        "iv_seed": iv_seed,
    }
