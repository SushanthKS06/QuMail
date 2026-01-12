"""
Status API

Provides key material availability and system status.
"""

import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel

from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


class KeyAvailability(BaseModel):
    """Available key material."""
    otp_bytes_available: int
    aes_keys_available: int
    pqc_keys_available: int


class SystemStatus(BaseModel):
    """Full system status."""
    healthy: bool
    simulation_mode: bool
    version: str
    available: KeyAvailability
    total_keys_allocated: int
    total_keys_consumed: int


@router.get("/keys/status", response_model=KeyAvailability)
async def get_key_status(request: Request, peer_id: str = None):
    """
    Get available key material.
    
    Optionally filter by peer_id.
    """
    key_pool = request.app.state.key_pool
    
    stats = key_pool.get_stats()
    
    return KeyAvailability(
        otp_bytes_available=stats["otp_available"],
        aes_keys_available=stats["aes_available"],
        pqc_keys_available=0,
    )


@router.get("/status", response_model=SystemStatus)
async def get_system_status(request: Request):
    """
    Get full system status.
    """
    key_pool = request.app.state.key_pool
    
    stats = key_pool.get_stats()
    
    return SystemStatus(
        healthy=True,
        simulation_mode=True,
        version=settings.app_version,
        available=KeyAvailability(
            otp_bytes_available=stats["otp_available"],
            aes_keys_available=stats["aes_available"],
            pqc_keys_available=0,
        ),
        total_keys_allocated=stats["total_allocated"],
        total_keys_consumed=stats["total_consumed"],
    )
