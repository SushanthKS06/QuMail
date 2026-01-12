import base64
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter()


class KeyRequestBody(BaseModel):
    peer_id: str
    size: int = Field(gt=0, le=1024 * 1024)
    key_type: str = "aes_seed"


class KeyResponse(BaseModel):
    key_id: str
    key_material: str
    peer_id: str
    key_type: str
    created_at: str
    expires_at: Optional[str] = None


class KeyStatusResponse(BaseModel):
    key_id: str
    peer_id: str
    key_type: str
    used: bool
    created_at: str


class ConsumeResponse(BaseModel):
    success: bool
    consumed_at: str


class ProvisionRequest(BaseModel):
    key_type: str
    size: int


class ProvisionResponse(BaseModel):
    success: bool
    keys_added: int


@router.post("/request", response_model=KeyResponse)
async def request_key(request: Request, body: KeyRequestBody):
    key_pool = request.app.state.key_pool
    
    try:
        key_entry = key_pool.allocate_key(
            peer_id=body.peer_id,
            size=body.size,
            key_type=body.key_type,
        )
        
        logger.info(
            "Allocated key %s for peer %s, type=%s, size=%d",
            key_entry.key_id, body.peer_id, body.key_type, body.size
        )
        
        return KeyResponse(
            key_id=key_entry.key_id,
            key_material=base64.b64encode(key_entry.key_material).decode("ascii"),
            peer_id=key_entry.peer_id,
            key_type=key_entry.key_type,
            created_at=key_entry.created_at.isoformat(),
            expires_at=key_entry.expires_at.isoformat() if key_entry.expires_at else None,
        )
        
    except ValueError as e:
        logger.warning("Key request failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )


@router.get("/{key_id}", response_model=KeyResponse)
async def get_key(request: Request, key_id: str):
    key_pool = request.app.state.key_pool
    
    key_entry = key_pool.get_key(key_id)
    
    if key_entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Key {key_id} not found",
        )
    
    if key_entry.consumed:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=f"Key {key_id} has already been consumed (one-time use)",
        )
    
    return KeyResponse(
        key_id=key_entry.key_id,
        key_material=base64.b64encode(key_entry.key_material).decode("ascii"),
        peer_id=key_entry.peer_id,
        key_type=key_entry.key_type,
        created_at=key_entry.created_at.isoformat(),
    )


@router.post("/{key_id}/consume", response_model=ConsumeResponse)
async def consume_key(request: Request, key_id: str):
    key_pool = request.app.state.key_pool
    
    success = key_pool.consume_key(key_id)
    
    if not success:
        key_entry = key_pool.get_key(key_id)
        if key_entry is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Key {key_id} not found",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail=f"Key {key_id} already consumed",
            )
    
    logger.info("Key %s consumed (one-time use complete)", key_id)
    
    return ConsumeResponse(
        success=True,
        consumed_at=datetime.now(timezone.utc).isoformat(),
    )


@router.delete("/{key_id}")
async def delete_key(request: Request, key_id: str):
    key_pool = request.app.state.key_pool
    
    success = key_pool.delete_key(key_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Key {key_id} not found",
        )
    
    logger.warning("Key %s emergency deleted", key_id)
    
    return {
        "success": True,
        "zeroized_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/provision", response_model=ProvisionResponse)
async def provision_keys(request: Request, body: ProvisionRequest):
    key_pool = request.app.state.key_pool
    
    if body.key_type == "otp":
        key_pool.add_otp_material(body.size)
        keys_added = body.size
    elif body.key_type == "aes":
        key_pool.add_aes_keys(body.size)
        keys_added = body.size
    else:
        keys_added = 0
    
    logger.info("Provisioned %d %s keys/bytes", keys_added, body.key_type)
    
    return ProvisionResponse(
        success=True,
        keys_added=keys_added,
    )
