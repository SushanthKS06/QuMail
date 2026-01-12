from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


def derive_key(
    input_key_material: bytes,
    context: bytes,
    length: int,
    salt: bytes = b"",
) -> bytes:
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
    return [
        derive_key(input_key_material, context, length, salt)
        for context, length in contexts
    ]


def derive_email_keys(qkd_key: bytes, email_id: str) -> dict:
    base_context = f"qumail-email-{email_id}".encode()
    
    encryption_key = derive_key(qkd_key, base_context + b"-enc", 32)
    mac_key = derive_key(qkd_key, base_context + b"-mac", 32)
    iv_seed = derive_key(qkd_key, base_context + b"-iv", 16)
    
    return {
        "encryption_key": encryption_key,
        "mac_key": mac_key,
        "iv_seed": iv_seed,
    }
