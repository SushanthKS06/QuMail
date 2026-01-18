import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Optional

from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


class KeyAvailability(BaseModel):
    otp_bytes_available: int
    aes_keys_available: int
    pqc_keys_available: int


class ProductionFeatures(BaseModel):
    quantum_entropy: bool
    persistence_enabled: bool
    audit_logging: bool
    rate_limiting: bool
    multi_user: bool


class SystemStatus(BaseModel):
    healthy: bool
    production_ready: bool
    version: str
    available: KeyAvailability
    total_keys_allocated: int
    total_keys_consumed: int
    features: ProductionFeatures
    entropy_healthy: Optional[bool] = True


@router.get("/keys/status", response_model=KeyAvailability)
async def get_key_status(request: Request, peer_id: str = None):
    key_pool = request.app.state.key_pool
    
    stats = key_pool.get_stats()
    
    return KeyAvailability(
        otp_bytes_available=stats["otp_available"],
        aes_keys_available=stats["aes_available"],
        pqc_keys_available=0,
    )


@router.get("/status", response_model=SystemStatus)
async def get_system_status(request: Request):
    key_pool = request.app.state.key_pool
    
    stats = key_pool.get_stats()
    
    return SystemStatus(
        healthy=True,
        production_ready=True,
        version=settings.app_version,
        available=KeyAvailability(
            otp_bytes_available=stats["otp_available"],
            aes_keys_available=stats["aes_available"],
            pqc_keys_available=0,
        ),
        total_keys_allocated=stats["total_allocated"],
        total_keys_consumed=stats["total_consumed"],
        features=ProductionFeatures(
            quantum_entropy=stats.get("quantum_entropy", False),
            persistence_enabled=stats.get("persistence_enabled", False),
            audit_logging=settings.audit_enabled,
            rate_limiting=settings.rate_limit_enabled,
            multi_user=settings.multi_user_enabled,
        ),
        entropy_healthy=stats.get("entropy_healthy", True),
    )


@router.get("/user/{user_id}/stats")
async def get_user_stats(request: Request, user_id: str):
    key_pool = request.app.state.key_pool
    return key_pool.get_user_stats(user_id)


@router.get("/audit")
async def get_audit_log(request: Request, key_id: Optional[str] = None, limit: int = 100):
    key_pool = request.app.state.key_pool
    
    if hasattr(key_pool, "_audit_logger") and key_pool._audit_logger:
        entries = key_pool._audit_logger.get_entries(key_id=key_id, limit=limit)
        return {"entries": entries, "count": len(entries)}
    
    return {"entries": [], "count": 0, "audit_disabled": True}

