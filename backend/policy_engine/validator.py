"""
Request Validation

Validates email send requests against security policies.
"""

import logging
from typing import Any, Dict, List

from config import settings
from .rules import SecurityRules
from .fallback import get_fallback_level

logger = logging.getLogger(__name__)

_rules = SecurityRules()


async def validate_send_request(
    recipients: List[str],
    security_level: int,
    body_size: int,
    attachment_sizes: List[int] = None,
) -> Dict[str, Any]:
    """
    Validate an email send request.
    
    Checks:
    - Security level is valid (1-4)
    - Recipients support the requested level
    - Sufficient key material is available
    - Message size is within limits for OTP
    
    Args:
        recipients: List of recipient email addresses
        security_level: Requested security level (1-4)
        body_size: Size of email body in bytes
        attachment_sizes: Sizes of attachments in bytes
    
    Returns:
        Dict with:
        - valid: True if request is valid
        - error: Error message if invalid
        - adjusted_level: Adjusted level if fallback applied
        - warnings: Any warnings
    """
    attachment_sizes = attachment_sizes or []
    total_size = body_size + sum(attachment_sizes)
    
    if security_level < 1 or security_level > 4:
        return {
            "valid": False,
            "error": f"Invalid security level: {security_level}. Must be 1-4.",
        }
    
    if security_level == 4:
        return {"valid": True, "adjusted_level": 4}
    
    recipient_caps = []
    for recipient in recipients:
        cap = await check_recipient_capability(recipient)
        recipient_caps.append(cap)
    
    unsupported = [
        r["email"] for r in recipient_caps
        if security_level not in r.get("supported_levels", [4])
    ]
    
    if unsupported and security_level < 4:
        fallback = get_fallback_level(security_level, recipient_caps)
        
        if fallback == security_level:
            return {
                "valid": False,
                "error": f"Recipients {unsupported} do not support security level {security_level}",
            }
        
        logger.warning(
            "Falling back from level %d to %d for recipients %s",
            security_level, fallback, unsupported
        )
        
        return {
            "valid": True,
            "adjusted_level": fallback,
            "warnings": [f"Downgraded to level {fallback} for compatibility"],
        }
    
    if security_level == 1:
        from qkd_client import get_key_status
        
        status = await get_key_status()
        available_otp = status.get("available", {}).get("otp_bytes", 0)
        
        if available_otp < total_size:
            return {
                "valid": False,
                "error": (
                    f"Insufficient OTP key material. "
                    f"Required: {total_size} bytes, Available: {available_otp} bytes. "
                    f"Please use Level 2 (AES) or request more key material."
                ),
            }
    
    if security_level in (2, 3):
        from qkd_client import get_key_status
        
        status = await get_key_status()
        if not status.get("connected"):
            logger.warning("Key Manager not connected, falling back to level 4")
            return {
                "valid": True,
                "adjusted_level": 4,
                "warnings": ["Key Manager unavailable, sending without encryption"],
            }
    
    return {
        "valid": True,
        "adjusted_level": security_level,
    }


async def check_recipient_capability(email: str) -> Dict[str, Any]:
    """
    Check a recipient's QuMail capabilities.
    
    Args:
        email: Recipient email address
    
    Returns:
        Dict with email, is_qumail_user, and supported_levels
    """
    from storage.database import get_known_recipient
    
    recipient = await get_known_recipient(email)
    
    if recipient:
        return {
            "email": email,
            "is_qumail_user": True,
            "supported_levels": recipient.get("supported_levels", [2, 3, 4]),
            "public_key": recipient.get("public_key"),
        }
    
    return {
        "email": email,
        "is_qumail_user": False,
        "supported_levels": [4],
    }
