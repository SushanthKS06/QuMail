import base64
import json
import logging
from typing import Any, Dict, List, Optional

from .otp import otp_encrypt, otp_decrypt
from .aes_gcm import aes_encrypt, aes_decrypt
from .pqc import pqc_encrypt, pqc_decrypt
from .key_derivation import derive_key
from .secure_random import secure_random_bytes

logger = logging.getLogger(__name__)


async def encrypt_email(
    body: str,
    security_level: int,
    recipients: List[str],
    attachments: Optional[List[bytes]] = None,
) -> Dict[str, Any]:
    if security_level == 4:
        return {
            "ciphertext": body,
            "key_id": None,
            "metadata": {"security_level": 4},
        }
    
    if security_level == 1:
        result = await _encrypt_otp(body, recipients)
    elif security_level == 2:
        result = await _encrypt_aes(body, recipients)
    elif security_level == 3:
        result = await _encrypt_pqc(body, recipients)
    else:
        raise ValueError(f"Invalid security level: {security_level}")
    
    if attachments:
        encrypted_attachments = []
        for att in attachments:
            enc_att = await _encrypt_attachment(att, security_level, result.get("key_id"))
            encrypted_attachments.append(enc_att)
        result["attachments"] = encrypted_attachments
    
    return result


async def decrypt_email(email: Dict[str, Any]) -> Dict[str, Any]:
    security_level = email.get("security_level", 4)
    
    if security_level == 4:
        return {"body": email.get("body", "")}
    
    encrypted_body = email.get("encrypted_body") or email.get("body", "")
    key_id = email.get("key_id")
    metadata = email.get("encryption_metadata", {})
    
    if security_level == 1:
        plaintext = await _decrypt_otp(encrypted_body, key_id, metadata)
    elif security_level == 2:
        plaintext = await _decrypt_aes(encrypted_body, key_id, metadata)
    elif security_level == 3:
        plaintext = await _decrypt_pqc(encrypted_body, key_id, metadata)
    else:
        raise ValueError(f"Invalid security level: {security_level}")
    
    return {
        "body": plaintext,
        "preview": plaintext[:200] if plaintext else "",
    }


async def decrypt_attachment(
    content: bytes,
    key_id: Optional[str],
    security_level: int,
) -> bytes:
    if security_level == 4:
        return content
    
    try:
        decoded = base64.b64decode(content)
        envelope = json.loads(decoded[:decoded.index(b'\x00')])
        ciphertext = decoded[decoded.index(b'\x00') + 1:]
    except:
        envelope = {}
        ciphertext = content
    
    if security_level == 1:
        return await _decrypt_otp_bytes(ciphertext, key_id, envelope)
    elif security_level == 2:
        return await _decrypt_aes_bytes(ciphertext, key_id, envelope)
    elif security_level == 3:
        return await _decrypt_pqc_bytes(ciphertext, key_id, envelope)
    
    return content


async def _encrypt_otp(body: str, recipients: List[str]) -> Dict[str, Any]:
    from qkd_client import request_key
    
    body_bytes = body.encode('utf-8')
    key_size = len(body_bytes)
    
    key_response = await request_key(
        peer_id=recipients[0],
        size=key_size,
        key_type="otp",
    )
    
    ciphertext = otp_encrypt(body_bytes, key_response["key_material"])
    
    metadata = {
        "version": "1.0",
        "security_level": 1,
        "algorithm": "OTP-XOR",
        "key_id": key_response["key_id"],
        "body_length": key_size,
    }
    
    envelope = {
        **metadata,
        "ciphertext": base64.b64encode(ciphertext).decode('ascii'),
    }
    
    return {
        "ciphertext": base64.b64encode(json.dumps(envelope).encode()).decode('ascii'),
        "key_id": key_response["key_id"],
        "metadata": metadata,
    }


async def _encrypt_aes(body: str, recipients: List[str]) -> Dict[str, Any]:
    from qkd_client import request_key
    
    key_response = await request_key(
        peer_id=recipients[0],
        size=32,
        key_type="aes_seed",
    )
    
    aes_key = derive_key(key_response["key_material"], b"qumail-aes-encryption", 32)
    
    ciphertext, nonce, tag = aes_encrypt(body.encode('utf-8'), aes_key)
    
    metadata = {
        "version": "1.0",
        "security_level": 2,
        "algorithm": "AES-256-GCM",
        "key_id": key_response["key_id"],
    }
    
    envelope = {
        **metadata,
        "nonce": base64.b64encode(nonce).decode('ascii'),
        "tag": base64.b64encode(tag).decode('ascii'),
        "ciphertext": base64.b64encode(ciphertext).decode('ascii'),
    }
    
    return {
        "ciphertext": base64.b64encode(json.dumps(envelope).encode()).decode('ascii'),
        "key_id": key_response["key_id"],
        "metadata": metadata,
    }


async def _encrypt_pqc(body: str, recipients: List[str]) -> Dict[str, Any]:
    from qkd_client import request_key
    from storage.database import get_known_recipient
    
    recipient = await get_known_recipient(recipients[0])
    recipient_public_key = recipient.get("public_key") if recipient else None
    
    ciphertext, encapsulated_key, shared_secret = pqc_encrypt(
        body.encode('utf-8'),
        recipient_public_key,
    )
    
    key_response = await request_key(
        peer_id=recipients[0],
        size=32,
        key_type="aes_seed",
    )
    
    combined_key = derive_key(
        shared_secret + key_response["key_material"],
        b"qumail-pqc-hybrid",
        32,
    )
    
    aes_ciphertext, nonce, tag = aes_encrypt(body.encode('utf-8'), combined_key)
    
    metadata = {
        "version": "1.0",
        "security_level": 3,
        "algorithm": "KYBER-768-AES-256-GCM",
        "key_id": key_response["key_id"],
    }
    
    envelope = {
        **metadata,
        "encapsulated_key": base64.b64encode(encapsulated_key).decode('ascii'),
        "nonce": base64.b64encode(nonce).decode('ascii'),
        "tag": base64.b64encode(tag).decode('ascii'),
        "ciphertext": base64.b64encode(aes_ciphertext).decode('ascii'),
    }
    
    return {
        "ciphertext": base64.b64encode(json.dumps(envelope).encode()).decode('ascii'),
        "key_id": key_response["key_id"],
        "metadata": metadata,
    }


async def _decrypt_otp(
    encrypted_body: str,
    key_id: Optional[str],
    metadata: Dict[str, Any],
) -> str:
    from qkd_client import get_key
    
    envelope = json.loads(base64.b64decode(encrypted_body))
    ciphertext = base64.b64decode(envelope["ciphertext"])
    
    key_response = await get_key(envelope.get("key_id") or key_id)
    
    plaintext = otp_decrypt(ciphertext, key_response["key_material"])
    
    return plaintext.decode('utf-8')


async def _decrypt_aes(
    encrypted_body: str,
    key_id: Optional[str],
    metadata: Dict[str, Any],
) -> str:
    from qkd_client import get_key
    
    envelope = json.loads(base64.b64decode(encrypted_body))
    
    ciphertext = base64.b64decode(envelope["ciphertext"])
    nonce = base64.b64decode(envelope["nonce"])
    tag = base64.b64decode(envelope["tag"])
    
    key_response = await get_key(envelope.get("key_id") or key_id)
    
    aes_key = derive_key(key_response["key_material"], b"qumail-aes-encryption", 32)
    
    plaintext = aes_decrypt(ciphertext, aes_key, nonce, tag)
    
    return plaintext.decode('utf-8')


async def _decrypt_pqc(
    encrypted_body: str,
    key_id: Optional[str],
    metadata: Dict[str, Any],
) -> str:
    from qkd_client import get_key
    from key_store import get_private_key
    
    envelope = json.loads(base64.b64decode(encrypted_body))
    
    encapsulated_key = base64.b64decode(envelope["encapsulated_key"])
    ciphertext = base64.b64decode(envelope["ciphertext"])
    nonce = base64.b64decode(envelope["nonce"])
    tag = base64.b64decode(envelope["tag"])
    
    private_key = await get_private_key("pqc")
    shared_secret = pqc_decrypt(encapsulated_key, private_key)
    
    key_response = await get_key(envelope.get("key_id") or key_id)
    
    combined_key = derive_key(
        shared_secret + key_response["key_material"],
        b"qumail-pqc-hybrid",
        32,
    )
    
    plaintext = aes_decrypt(ciphertext, combined_key, nonce, tag)
    
    return plaintext.decode('utf-8')


async def _encrypt_attachment(
    content: bytes,
    security_level: int,
    key_id: Optional[str],
) -> bytes:
    from qkd_client import get_key
    
    if security_level == 2:
        key_response = await get_key(key_id)
        aes_key = derive_key(key_response["key_material"], b"qumail-attachment", 32)
        ciphertext, nonce, tag = aes_encrypt(content, aes_key)
        
        envelope = {
            "nonce": base64.b64encode(nonce).decode('ascii'),
            "tag": base64.b64encode(tag).decode('ascii'),
        }
        return json.dumps(envelope).encode() + b'\x00' + ciphertext
    
    return content


async def _decrypt_otp_bytes(
    ciphertext: bytes,
    key_id: Optional[str],
    envelope: Dict[str, Any],
) -> bytes:
    from qkd_client import get_key
    key_response = await get_key(key_id)
    return otp_decrypt(ciphertext, key_response["key_material"])


async def _decrypt_aes_bytes(
    ciphertext: bytes,
    key_id: Optional[str],
    envelope: Dict[str, Any],
) -> bytes:
    from qkd_client import get_key
    
    key_response = await get_key(key_id)
    aes_key = derive_key(key_response["key_material"], b"qumail-attachment", 32)
    
    nonce = base64.b64decode(envelope.get("nonce", ""))
    tag = base64.b64decode(envelope.get("tag", ""))
    
    return aes_decrypt(ciphertext, aes_key, nonce, tag)


async def _decrypt_pqc_bytes(
    ciphertext: bytes,
    key_id: Optional[str],
    envelope: Dict[str, Any],
) -> bytes:
    from qkd_client import get_key
    from key_store import get_private_key
    
    encapsulated_key = base64.b64decode(envelope.get("encapsulated_key", ""))
    private_key = await get_private_key("pqc")
    shared_secret = pqc_decrypt(encapsulated_key, private_key)
    
    key_response = await get_key(key_id)
    combined_key = derive_key(
        shared_secret + key_response["key_material"],
        b"qumail-pqc-hybrid",
        32,
    )
    
    nonce = base64.b64decode(envelope.get("nonce", ""))
    tag = base64.b64decode(envelope.get("tag", ""))
    
    return aes_decrypt(ciphertext, combined_key, nonce, tag)
