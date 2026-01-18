import base64
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

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
    attachments: Optional[List[dict]] = None,
) -> Dict[str, Any]:
    if security_level == 4:
        return {
            "ciphertext": body,
            "key_id": None,
            "metadata": {"security_level": 4},
        }
    
    # 1. Encrypt Body & Establish Session Context
    session_key = None
    if security_level == 1:
        # OTP has no session key reuse for attachments (each needs fresh OTP)
        result, _ = await _encrypt_otp(body, recipients)
    elif security_level == 2:
        result, session_key = await _encrypt_aes(body, recipients)
    elif security_level == 3:
        result, session_key = await _encrypt_pqc(body, recipients)
    else:
        raise ValueError(f"Invalid security level: {security_level}")
    
    # 2. Encrypt Attachments using Session Context or New OTP
    if attachments:
        encrypted_attachments = []
        for att in attachments:
            enc_att = await _encrypt_attachment(
                content=att["content"],
                security_level=security_level,
                session_key=session_key,
                recipients=recipients
            )
            encrypted_attachments.append({
                "filename": att["filename"],
                "content": enc_att
            })
        result["attachments"] = encrypted_attachments
    
    return result


async def decrypt_email(email: Dict[str, Any]) -> Dict[str, Any]:
    security_level = email.get("security_level", 4)
    
    if security_level == 4:
        return {"body": email.get("body", "")}
    
    encrypted_body = email.get("encrypted_body") or email.get("body", "")
    key_id = email.get("key_id")
    metadata = email.get("encryption_metadata", {})
    
    # Decrypt body and recover session key if applicable
    session_key = None
    plaintext = ""
    
    if security_level == 1:
        plaintext, _ = await _decrypt_otp(encrypted_body, key_id, metadata)
    elif security_level == 2:
        plaintext, session_key = await _decrypt_aes(encrypted_body, key_id, metadata)
    elif security_level == 3:
        plaintext, session_key = await _decrypt_pqc(encrypted_body, key_id, metadata, email.get("from"))
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
        # Check if it looks like JSON
        try:
            envelope = json.loads(content)
        except:
            # Maybe it's base64 encoded JSON
            decoded = base64.b64decode(content)
            envelope = json.loads(decoded)
            
    except Exception:
        # Fallback to return raw if failed
        return content

    # Now we have the envelope
    att_level = envelope.get("security_level", security_level)
    att_key_id = envelope.get("key_id", key_id)
    
    # Delegate to decryptors
    if att_level == 1:
        return await _decrypt_otp_bytes(envelope, att_key_id)
    elif att_level == 2:
        return await _decrypt_aes_bytes(envelope, att_key_id)
    elif att_level == 3:
        return await _decrypt_pqc_bytes(envelope, att_key_id)
    
    return content


async def _encrypt_otp(body: str, recipients: List[str]) -> Tuple[Dict[str, Any], None]:
    from qkd_client import request_key, consume_key
    
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
    }, None


async def _encrypt_aes(body: str, recipients: List[str]) -> Tuple[Dict[str, Any], bytes]:
    from qkd_client import request_key
    
    recipient_keys = {}
    primary_key_response = None
    
    for recipient in recipients:
        key_response = await request_key(
            peer_id=recipient,
            size=32,
            key_type="aes_seed",
        )
        recipient_keys[recipient] = key_response["key_id"]
        if primary_key_response is None:
            primary_key_response = key_response
    
    aes_key = derive_key(primary_key_response["key_material"], b"qumail-aes-encryption", 32)
    
    ciphertext, nonce, tag = aes_encrypt(body.encode('utf-8'), aes_key)
    
    metadata = {
        "version": "1.0",
        "security_level": 2,
        "algorithm": "AES-256-GCM",
        "key_id": primary_key_response["key_id"],
        "recipient_key_ids": recipient_keys,
    }
    
    envelope = {
        **metadata,
        "nonce": base64.b64encode(nonce).decode('ascii'),
        "tag": base64.b64encode(tag).decode('ascii'),
        "ciphertext": base64.b64encode(ciphertext).decode('ascii'),
    }
    
    return {
        "ciphertext": base64.b64encode(json.dumps(envelope).encode()).decode('ascii'),
        "key_id": primary_key_response["key_id"],
        "metadata": metadata,
    }, aes_key


async def _encrypt_pqc(body: str, recipients: List[str]) -> Tuple[Dict[str, Any], bytes]:
    from qkd_client import request_key
    from storage.database import get_known_recipient
    from .pqc import dilithium_sign, generate_dilithium_keypair
    from key_store import get_private_key, store_private_key
    
    recipient = await get_known_recipient(recipients[0])
    recipient_public_key = recipient.get("public_key") if recipient else None
    
    ciphertext_dummy, encapsulated_key, shared_secret = pqc_encrypt(
        body.encode('utf-8'), # Input ignored by pqc_encrypt, it returns session keys
        recipient_public_key,
    )
    
    recipient_keys = {}
    primary_key_response = None
    
    for r in recipients:
        key_response = await request_key(
            peer_id=r,
            size=32,
            key_type="aes_seed",
        )
        recipient_keys[r] = key_response["key_id"]
        if primary_key_response is None:
            primary_key_response = key_response
    
    combined_key = derive_key(
        shared_secret + primary_key_response["key_material"],
        b"qumail-pqc-hybrid",
        32,
    )
    
    aes_ciphertext, nonce, tag = aes_encrypt(body.encode('utf-8'), combined_key)
    
    try:
        signing_key = await get_private_key("dilithium")
        if signing_key is None:
            _, signing_key = generate_dilithium_keypair()
            await store_private_key("dilithium", signing_key)
    except Exception:
        _, signing_key = generate_dilithium_keypair()
    
    message_hash = aes_ciphertext + nonce + tag
    signature = dilithium_sign(message_hash, signing_key)
    
    metadata = {
        "version": "1.0",
        "security_level": 3,
        "algorithm": "KYBER-768-DILITHIUM3-AES-256-GCM",
        "key_id": primary_key_response["key_id"],
        "recipient_key_ids": recipient_keys,
        "signed": True,
    }
    
    envelope = {
        **metadata,
        "encapsulated_key": base64.b64encode(encapsulated_key).decode('ascii'),
        "nonce": base64.b64encode(nonce).decode('ascii'),
        "tag": base64.b64encode(tag).decode('ascii'),
        "ciphertext": base64.b64encode(aes_ciphertext).decode('ascii'),
        "signature": base64.b64encode(signature).decode('ascii'),
    }
    
    return {
        "ciphertext": base64.b64encode(json.dumps(envelope).encode()).decode('ascii'),
        "key_id": primary_key_response["key_id"],
        "metadata": metadata,
    }, combined_key


async def _encrypt_attachment(
    content: bytes,
    security_level: int,
    session_key: Optional[bytes],
    recipients: List[str]
) -> bytes:
    """
    Independent encryption for attachments.
    Ensures that EVERY attachment is encrypted securely according to the level.
    """
    if security_level == 1:
        # OTP: Need a fresh key for this specific content
        from qkd_client import request_key, consume_key
        key_size = len(content)
        key_response = await request_key(
            peer_id=recipients[0],
            size=key_size,
            key_type="otp",
        )
        ciphertext = otp_encrypt(content, key_response["key_material"])
        envelope = {
            "version": "1.0",
            "security_level": 1,
            "key_id": key_response["key_id"],
            "ciphertext": base64.b64encode(ciphertext).decode('ascii')
        }
        return base64.b64encode(json.dumps(envelope).encode())

    elif security_level == 2:
        # AES: Independent Encryption (new nonce/tag) with NEW key for statelessness
        from qkd_client import request_key
        key_response = await request_key(recipients[0], 32, "aes_seed")
        aes_key = derive_key(key_response["key_material"], b"qumail-attachment", 32)
        ciphertext, nonce, tag = aes_encrypt(content, aes_key)
        
        envelope = {
            "version": "1.0",
            "security_level": 2,
            "key_id": key_response["key_id"],
            "nonce": base64.b64encode(nonce).decode('ascii'),
            "tag": base64.b64encode(tag).decode('ascii'),
            "ciphertext": base64.b64encode(ciphertext).decode('ascii')
        }
        return base64.b64encode(json.dumps(envelope).encode())

    elif security_level == 3:
        # PQC: Independent Encryption
        from qkd_client import request_key
        from storage.database import get_known_recipient
        from .pqc import pqc_encrypt
        
        recipient = await get_known_recipient(recipients[0])
        pub_key = recipient.get("public_key") if recipient else None
        
        _, encapsulated_key, shared_secret = pqc_encrypt(b"", pub_key)
        key_response = await request_key(recipients[0], 32, "aes_seed")
        
        combined_key = derive_key(shared_secret + key_response["key_material"], b"qumail-pqc-hybrid", 32)
        
        ciphertext, nonce, tag = aes_encrypt(content, combined_key)
        
        envelope = {
            "version": "1.0",
            "security_level": 3,
            "key_id": key_response["key_id"],
            "encapsulated_key": base64.b64encode(encapsulated_key).decode('ascii'),
            "nonce": base64.b64encode(nonce).decode('ascii'),
            "tag": base64.b64encode(tag).decode('ascii'),
            "ciphertext": base64.b64encode(ciphertext).decode('ascii')
        }
        return base64.b64encode(json.dumps(envelope).encode())

    return content



async def _decrypt_otp(ciphertext_b64: str, key_id: str, metadata: dict) -> Tuple[str, None]:
    from qkd_client import get_key, consume_key
    
    try:
        envelope_json = base64.b64decode(ciphertext_b64)
        envelope = json.loads(envelope_json)
    except Exception:
        return "", None
        
    actual_key_id = envelope.get("key_id", key_id)
    ct_bytes = base64.b64decode(envelope["ciphertext"])
    
    key_response = await get_key(actual_key_id)
    plaintext_bytes = otp_decrypt(ct_bytes, key_response["key_material"])
    
    try:
        await consume_key(actual_key_id)
    except Exception as e:
        logger.warning(f"Failed to consume OTP key {actual_key_id}: {e}")
        
    return plaintext_bytes.decode('utf-8', errors='replace'), None


async def _decrypt_aes(ciphertext_b64: str, key_id: str, metadata: dict) -> Tuple[str, bytes]:
    from qkd_client import get_key
    
    envelope_json = base64.b64decode(ciphertext_b64)
    envelope = json.loads(envelope_json)
    
    actual_key_id = envelope.get("key_id", key_id)
    key_response = await get_key(actual_key_id)
    
    aes_key = derive_key(key_response["key_material"], b"qumail-aes-encryption", 32)
    
    nonce = base64.b64decode(envelope["nonce"])
    tag = base64.b64decode(envelope["tag"])
    ct = base64.b64decode(envelope["ciphertext"])
    
    plaintext_bytes = aes_decrypt(ct, aes_key, nonce, tag)
    
    return plaintext_bytes.decode('utf-8', errors='replace'), aes_key


async def _decrypt_pqc(ciphertext_b64: str, key_id: str, metadata: dict, sender: Optional[str] = None) -> Tuple[str, bytes]:
    from qkd_client import get_key
    from .pqc import pqc_decrypt, dilithium_verify
    from key_store import get_private_key
    from storage.database import get_known_recipient
    import re
    
    envelope_json = base64.b64decode(ciphertext_b64)
    envelope = json.loads(envelope_json)
    
    if envelope.get("signature") and sender:
         match = re.search(r'<([^>]+)>', sender)
         sender_email = match.group(1) if match else sender
         
         sender_info = await get_known_recipient(sender_email)
         if sender_info and sender_info.get("signing_key"):
             public_key = sender_info["signing_key"]
             
             aes_ct = base64.b64decode(envelope["ciphertext"])
             nonce = base64.b64decode(envelope["nonce"])
             tag = base64.b64decode(envelope["tag"])
             message_hash = aes_ct + nonce + tag
             
             signature = base64.b64decode(envelope["signature"])
             
             if not dilithium_verify(message_hash, signature, public_key):
                 logger.error("Dilithium signature verification failed for sender %s", sender)

    target_key_id = envelope.get("key_id", key_id)
    encapsulated_key = base64.b64decode(envelope["encapsulated_key"])
    private_key = await get_private_key("pqc")
    shared_secret = pqc_decrypt(encapsulated_key, private_key)
    
    key_response = await get_key(target_key_id)
    combined_key = derive_key(
        shared_secret + key_response["key_material"],
        b"qumail-pqc-hybrid",
        32,
    )
    
    nonce = base64.b64decode(envelope["nonce"])
    tag = base64.b64decode(envelope["tag"])
    ciphertext = base64.b64decode(envelope["ciphertext"])
    
    plaintext_bytes = aes_decrypt(ciphertext, combined_key, nonce, tag)
    
    return plaintext_bytes.decode('utf-8', errors='replace'), combined_key


async def _decrypt_otp_bytes(envelope: Dict[str, Any], key_id: str) -> bytes:
    from qkd_client import get_key
    
    ciphertext = base64.b64decode(envelope["ciphertext"])
    target_key_id = envelope.get("key_id", key_id)
    
    key_response = await get_key(target_key_id)
    return otp_decrypt(ciphertext, key_response["key_material"])


async def _decrypt_aes_bytes(envelope: Dict[str, Any], key_id: str) -> bytes:
    from qkd_client import get_key
    
    target_key_id = envelope.get("key_id", key_id)
    key_response = await get_key(target_key_id)
    aes_key = derive_key(key_response["key_material"], b"qumail-attachment", 32)
    
    nonce = base64.b64decode(envelope["nonce"])
    tag = base64.b64decode(envelope["tag"])
    ciphertext = base64.b64decode(envelope["ciphertext"])
    
    return aes_decrypt(ciphertext, aes_key, nonce, tag)


async def _decrypt_pqc_bytes(envelope: Dict[str, Any], key_id: str) -> bytes:
    from qkd_client import get_key
    from key_store import get_private_key
    
    target_key_id = envelope.get("key_id", key_id)
    
    encapsulated_key = base64.b64decode(envelope["encapsulated_key"])
    private_key = await get_private_key("pqc")
    shared_secret = pqc_decrypt(encapsulated_key, private_key)
    
    key_response = await get_key(target_key_id)
    
    combined_key = derive_key(
        shared_secret + key_response["key_material"],
        b"qumail-pqc-hybrid",
        32,
    )
    
    nonce = base64.b64decode(envelope["nonce"])
    tag = base64.b64decode(envelope["tag"])
    ciphertext = base64.b64decode(envelope["ciphertext"])
    
    return aes_decrypt(ciphertext, combined_key, nonce, tag)
