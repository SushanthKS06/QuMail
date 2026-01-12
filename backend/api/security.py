"""
Security API Routes

Provides security status, key management, and recipient capability checking.
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from api.dependencies import TokenDep
from config import settings
from qkd_client import get_key_status, request_key_refresh, KeyRequestError

logger = logging.getLogger(__name__)
router = APIRouter()


class KeyMaterialStatus(BaseModel):
    """Available key material status."""
    otp_bytes: int
    aes_keys: int
    pqc_keys: int


class SecurityStatus(BaseModel):
    """Overall security status."""
    km_connected: bool
    km_url: str
    available_key_material: KeyMaterialStatus
    last_key_sync: Optional[datetime] = None
    supported_levels: List[int]


class RecipientCapability(BaseModel):
    """Recipient's QuMail capabilities."""
    email: str
    is_qumail_user: bool
    supported_levels: List[int]
    public_key_fingerprint: Optional[str] = None
    last_seen: Optional[datetime] = None


class KeyRefreshRequest(BaseModel):
    """Request for key material refresh."""
    key_type: str
    size: int


class KeyRefreshResponse(BaseModel):
    """Response after key refresh."""
    success: bool
    keys_added: int
    error: Optional[str] = None


@router.get("/status", response_model=SecurityStatus)
async def get_security_status(token: TokenDep):
    """
    Get current security status including Key Manager connectivity
    and available key material.
    """
    try:
        km_status = await get_key_status()
        
        supported_levels = [4]
        if km_status["connected"]:
            if km_status["available"].get("otp_bytes", 0) > 0:
                supported_levels.insert(0, 1)
            if km_status["available"].get("aes_keys", 0) > 0:
                supported_levels.insert(0, 2)
            if km_status["available"].get("pqc_keys", 0) > 0:
                supported_levels.insert(0, 3)
        
        return SecurityStatus(
            km_connected=km_status["connected"],
            km_url=settings.km_url,
            available_key_material=KeyMaterialStatus(
                otp_bytes=km_status["available"].get("otp_bytes", 0),
                aes_keys=km_status["available"].get("aes_keys", 0),
                pqc_keys=km_status["available"].get("pqc_keys", 0),
            ),
            last_key_sync=km_status.get("last_sync"),
            supported_levels=sorted(supported_levels),
        )
        
    except Exception as e:
        logger.exception("Failed to get security status: %s", e)
        return SecurityStatus(
            km_connected=False,
            km_url=settings.km_url,
            available_key_material=KeyMaterialStatus(
                otp_bytes=0,
                aes_keys=0,
                pqc_keys=0,
            ),
            supported_levels=[4],
        )


@router.get("/capabilities/{email}", response_model=RecipientCapability)
async def check_recipient_capability(token: TokenDep, email: EmailStr):
    """
    Check if a recipient is a QuMail user and what security levels
    they support.
    
    This is used to determine available security options when composing
    an email.
    """
    from storage.database import get_known_recipient
    
    recipient = await get_known_recipient(email)
    
    if recipient:
        return RecipientCapability(
            email=email,
            is_qumail_user=True,
            supported_levels=recipient.get("supported_levels", [2, 3, 4]),
            public_key_fingerprint=recipient.get("public_key_fingerprint"),
            last_seen=recipient.get("last_seen"),
        )
    
    return RecipientCapability(
        email=email,
        is_qumail_user=False,
        supported_levels=[4],
    )


@router.post("/refresh-keys", response_model=KeyRefreshResponse)
async def refresh_keys(token: TokenDep, request: KeyRefreshRequest):
    """
    Request new key material from the Key Manager.
    
    This proactively fetches key material to ensure sufficient
    keys are available for encryption.
    """
    if request.key_type not in ("otp", "aes", "pqc"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="key_type must be one of: otp, aes, pqc",
        )
    
    if request.size <= 0 or request.size > 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="size must be between 1 and 1MB",
        )
    
    try:
        result = await request_key_refresh(
            key_type=request.key_type,
            size=request.size,
        )
        
        return KeyRefreshResponse(
            success=True,
            keys_added=result["keys_added"],
        )
        
    except KeyRequestError as e:
        logger.error("Key refresh failed: %s", e)
        return KeyRefreshResponse(
            success=False,
            keys_added=0,
            error=str(e),
        )
    except Exception as e:
        logger.exception("Unexpected error during key refresh: %s", e)
        return KeyRefreshResponse(
            success=False,
            keys_added=0,
            error="Internal error during key refresh",
        )


@router.get("/levels")
async def get_security_levels(token: TokenDep):
    """
    Get detailed information about available security levels.
    """
    return {
        "levels": [
            {
                "level": 1,
                "name": "Quantum Secure OTP",
                "description": "One-Time Pad encryption with QKD-distributed keys. "
                              "Provides information-theoretic security - unbreakable "
                              "even with unlimited computational power.",
                "requirements": "Key material length must equal message length",
                "quantum_safe": True,
                "recommended_for": "Highly sensitive communications",
            },
            {
                "level": 2,
                "name": "Quantum-Aided AES",
                "description": "AES-256-GCM encryption with keys derived from QKD material. "
                              "Quantum-derived randomness enhances key unpredictability.",
                "requirements": "32 bytes of QKD key material per message",
                "quantum_safe": False,
                "recommended_for": "Default for most communications",
            },
            {
                "level": 3,
                "name": "Post-Quantum Crypto",
                "description": "Kyber key encapsulation with optional Dilithium signatures. "
                              "Resistant to quantum computer attacks using lattice-based cryptography.",
                "requirements": "Recipient's PQC public key",
                "quantum_safe": True,
                "recommended_for": "Long-term confidentiality needs",
            },
            {
                "level": 4,
                "name": "No Security",
                "description": "Plain text email with no encryption. "
                              "Use for compatibility with non-QuMail recipients.",
                "requirements": "None",
                "quantum_safe": False,
                "recommended_for": "Non-sensitive communications",
            },
        ],
        "default_level": settings.default_security_level,
    }


@router.post("/register-recipient")
async def register_recipient(
    token: TokenDep,
    email: EmailStr,
    public_key: Optional[str] = None,
):
    """
    Register a known QuMail recipient for PQC key exchange.
    
    This stores the recipient's public key for Level 3 encryption.
    """
    from storage.database import store_known_recipient
    
    await store_known_recipient(
        email=email,
        public_key=public_key,
        supported_levels=[2, 3, 4] if public_key else [4],
    )
    
    return {"success": True, "email": email}
