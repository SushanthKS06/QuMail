import base64
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx

from config import settings
from .models import KeyResponse, KeyStatusResponse
from .exceptions import KeyRequestError, KeyNotFoundError, KeyExhaustedError

logger = logging.getLogger(__name__)

_http_client: Optional[httpx.AsyncClient] = None
_last_sync: Optional[datetime] = None


async def _get_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            base_url=settings.km_url,
            timeout=settings.km_timeout,
            headers={
                "Authorization": f"Bearer {settings.km_token}",
                "Content-Type": "application/json",
            },
        )
    return _http_client


async def request_key(
    peer_id: str,
    size: int,
    key_type: str = "aes_seed",
) -> KeyResponse:
    global _last_sync
    client = await _get_client()
    
    try:
        response = await client.post(
            "/api/v1/keys/request",
            json={
                "peer_id": peer_id,
                "size": size,
                "key_type": key_type,
            },
        )
        
        if response.status_code == 503:
            raise KeyExhaustedError(f"Insufficient key material for {key_type}")
        
        if response.status_code != 200:
            logger.error("Key request failed: %s", response.text)
            raise KeyRequestError(f"Key request failed: {response.status_code}")
        
        data = response.json()
        _last_sync = datetime.now(timezone.utc)
        
        key_material = base64.b64decode(data["key_material"])
        
        logger.info(
            "Received key %s for peer %s, size=%d bytes",
            data["key_id"], peer_id, len(key_material)
        )
        
        return KeyResponse(
            key_id=data["key_id"],
            key_material=key_material,
            peer_id=peer_id,
            key_type=key_type,
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now(timezone.utc).isoformat())),
        )
        
    except httpx.ConnectError as e:
        logger.error("Cannot connect to Key Manager: %s", e)
        raise KeyRequestError("Key Manager not reachable")
    except httpx.TimeoutException as e:
        logger.error("Key Manager request timeout: %s", e)
        raise KeyRequestError("Key Manager request timed out")


async def get_key(key_id: str) -> KeyResponse:
    client = await _get_client()
    
    try:
        response = await client.get(f"/api/v1/keys/{key_id}")
        
        if response.status_code == 404:
            raise KeyNotFoundError(f"Key {key_id} not found")
        
        if response.status_code == 410:
            raise KeyExhaustedError(f"Key {key_id} already consumed")
        
        if response.status_code != 200:
            raise KeyRequestError(f"Get key failed: {response.status_code}")
        
        data = response.json()
        key_material = base64.b64decode(data["key_material"])
        
        return KeyResponse(
            key_id=data["key_id"],
            key_material=key_material,
            peer_id=data.get("peer_id", ""),
            key_type=data.get("key_type", "aes_seed"),
            used=data.get("used", False),
        )
        
    except httpx.ConnectError as e:
        logger.error("Cannot connect to Key Manager: %s", e)
        raise KeyRequestError("Key Manager not reachable")


async def consume_key(key_id: str) -> bool:
    client = await _get_client()
    
    try:
        response = await client.post(f"/api/v1/keys/{key_id}/consume")
        
        if response.status_code == 410:
            raise KeyExhaustedError(f"Key {key_id} already consumed")
        
        if response.status_code != 200:
            raise KeyRequestError(f"Consume key failed: {response.status_code}")
        
        logger.info("Key %s marked as consumed", key_id)
        return True
        
    except httpx.ConnectError:
        raise KeyRequestError("Key Manager not reachable")


async def get_key_status(peer_id: Optional[str] = None) -> Dict[str, Any]:
    client = await _get_client()
    
    try:
        params = {"peer_id": peer_id} if peer_id else {}
        response = await client.get("/api/v1/keys/status", params=params)
        
        if response.status_code != 200:
            return {
                "connected": False,
                "available": {"otp_bytes": 0, "aes_keys": 0, "pqc_keys": 0},
                "error": f"Status check failed: {response.status_code}",
            }
        
        data = response.json()
        
        return {
            "connected": True,
            "available": {
                "otp_bytes": data.get("otp_bytes_available", 0),
                "aes_keys": data.get("aes_keys_available", 0),
                "pqc_keys": data.get("pqc_keys_available", 0),
            },
            "last_sync": _last_sync,
        }
        
    except httpx.ConnectError:
        return {
            "connected": False,
            "available": {"otp_bytes": 0, "aes_keys": 0, "pqc_keys": 0},
            "error": "Key Manager not reachable",
        }
    except Exception as e:
        logger.exception("Status check error: %s", e)
        return {
            "connected": False,
            "available": {"otp_bytes": 0, "aes_keys": 0, "pqc_keys": 0},
            "error": str(e),
        }


async def request_key_refresh(key_type: str, size: int) -> Dict[str, Any]:
    client = await _get_client()
    
    try:
        response = await client.post(
            "/api/v1/keys/provision",
            json={
                "key_type": key_type,
                "size": size,
            },
        )
        
        if response.status_code != 200:
            raise KeyRequestError(f"Key refresh failed: {response.status_code}")
        
        data = response.json()
        return {"keys_added": data.get("keys_added", 0)}
        
    except httpx.ConnectError:
        raise KeyRequestError("Key Manager not reachable")
