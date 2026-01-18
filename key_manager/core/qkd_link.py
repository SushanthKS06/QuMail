import asyncio
import base64
import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)


class QKDLink:
    """
    Simulates a physical Quantum Key Distribution link.
    Responsible for synchronizing keys between distributed Key Manager instances.
    """
    
    def __init__(self):
        # Configure mTLS if enabled
        verify = True
        cert = None
        
        if settings.ssl_ca_file:
            verify = str(settings.ssl_ca_file)
            
        if settings.ssl_cert_file and settings.ssl_key_file:
            cert = (str(settings.ssl_cert_file), str(settings.ssl_key_file))
            
        self._http_client = httpx.AsyncClient(
            timeout=10.0,
            verify=verify,
            cert=cert
        )
        self._background_tasks = set()
    
    async def push_key(self, peer_id: str, key_entry: Any) -> bool:
        """
        Active push of generated key to the peer's Key Manager.
        Simulates the transmission of photons over fiber optics.
        """
        # Check if we have a configured URL for this peer
        peer_url = settings.peers.get(peer_id)
        if not peer_url:
            logger.debug(f"No configured QKD link for peer {peer_id}, skipping push")
            return False
            
        logger.info(f"QKD LINK: Pushing key {key_entry.key_id} to {peer_id} ({peer_url})")
        
        # Prepare the payload
        # In simulating a QKD link, we send the key material securely
        # In a real QKD system, this would be the post-processing synchronization phase
        payload = {
            "key_id": key_entry.key_id,
            "key_material_b64": base64.b64encode(key_entry.key_material).decode('ascii'),
            "peer_id": settings.local_peer_id,  # WE are the peer from their perspective
            "key_type": key_entry.key_type,
            "created_at": key_entry.created_at.isoformat(),
            "expires_at": key_entry.expires_at.isoformat() if key_entry.expires_at else None,
            "user_id": key_entry.user_id,
            "source": "qkd_link_push"
        }
        
        # Fire and forget (or rather, fire and log) to avoid blocking the main thread
        # In a robust system, this would go into a durable queue (Redpanda/RabbitMQ)
        task = asyncio.create_task(self._send_key(peer_url, payload))
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return True
    
    async def _send_key(self, url: str, payload: Dict[str, Any]) -> None:
        try:
            # Add authentication (simulating mutual authentication of QKD nodes)
            headers = {
                "X-QKD-Link-Secret": settings.qkd_link_secret,
                "Content-Type": "application/json"
            }
            
            response = await self._http_client.post(
                f"{url}/api/v1/keys/exchange", 
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                logger.info(f"QKD LINK: Successfully synchronized key {payload['key_id']}")
            else:
                logger.warning(f"QKD LINK: Failed to sync key {payload['key_id']}: {response.status_code} {response.text}")
                
        except Exception as e:
            logger.error(f"QKD LINK: Connection error pushing key: {e}")
            
    async def shutdown(self):
        await self._http_client.aclose()
        
    
# Global instance
_qkd_link: Optional[QKDLink] = None

def get_qkd_link() -> QKDLink:
    global _qkd_link
    if _qkd_link is None:
        _qkd_link = QKDLink()
    return _qkd_link
