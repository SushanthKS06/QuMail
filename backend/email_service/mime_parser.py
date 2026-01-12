import base64
import email
import json
import logging
from email.message import Message
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def parse_qumail_message(msg: Message) -> Dict[str, Any]:
    result = {
        "encrypted_body": None,
        "body": "",
        "metadata": {},
        "attachments": [],
    }
    
    result["metadata"]["version"] = msg.get("X-QuMail-Version", "1.0")
    result["metadata"]["security_level"] = int(msg.get("X-QuMail-Security-Level", "4"))
    result["metadata"]["key_id"] = msg.get("X-QuMail-Key-ID")
    result["metadata"]["algorithm"] = msg.get("X-QuMail-Algorithm")
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            
            if content_type == "application/x-qumail-envelope":
                payload = part.get_payload(decode=True)
                if payload:
                    result["encrypted_body"] = payload.decode("utf-8")
                    
                    try:
                        envelope = json.loads(base64.b64decode(payload))
                        result["metadata"].update({
                            k: v for k, v in envelope.items()
                            if k not in ("ciphertext",)
                        })
                    except:
                        pass
            
            elif content_type == "application/x-qumail-attachment":
                original_name = part.get("X-QuMail-Original-Name", "attachment")
                original_size = int(part.get("X-QuMail-Original-Size", "0"))
                
                payload = part.get_payload(decode=True)
                
                result["attachments"].append({
                    "id": str(hash(original_name)),
                    "filename": original_name,
                    "content_type": "application/octet-stream",
                    "size": original_size,
                    "content": payload,
                    "encrypted": True,
                })
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            result["encrypted_body"] = payload.decode("utf-8")
    
    return result


def extract_envelope_data(encrypted_body: str) -> Dict[str, Any]:
    try:
        decoded = base64.b64decode(encrypted_body)
        envelope = json.loads(decoded)
        return envelope
    except Exception as e:
        logger.error("Failed to parse envelope: %s", e)
        return {}


def is_qumail_message(msg: Message) -> bool:
    return msg.get("X-QuMail-Version") is not None


def get_security_level(msg: Message) -> int:
    if not is_qumail_message(msg):
        return 4
    
    try:
        return int(msg.get("X-QuMail-Security-Level", "4"))
    except ValueError:
        return 4


def get_key_id(msg: Message) -> Optional[str]:
    return msg.get("X-QuMail-Key-ID")
