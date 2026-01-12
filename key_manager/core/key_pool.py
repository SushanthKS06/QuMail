"""
Key Pool Management

Manages the pool of QKD key material.
Simulates key generation using CSPRNG.

⚠️ SIMULATION: Real QKD uses quantum random number generation.
This uses os.urandom() which provides cryptographically secure
randomness but not true quantum randomness.
"""

import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


@dataclass
class KeyEntry:
    """A single key entry in the pool."""
    key_id: str
    key_material: bytes
    peer_id: str
    key_type: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    consumed: bool = False
    consumed_at: Optional[datetime] = None


class KeyPool:
    """
    Manages the simulated QKD key pool.
    
    In real QKD:
    - Keys come from quantum hardware
    - Keys are pre-shared between peers via quantum channel
    - Key rate depends on quantum link quality
    
    In simulation:
    - Keys are generated using CSPRNG
    - Unlimited key generation (bounded by config)
    - No actual peer synchronization
    """
    
    def __init__(self):
        self._lock = threading.RLock()
        self._otp_pool: bytearray = bytearray()
        self._otp_offset: int = 0
        self._aes_key_count: int = 0
        self._allocated_keys: Dict[str, KeyEntry] = {}
        self._stats = {
            "total_allocated": 0,
            "total_consumed": 0,
            "otp_bytes_used": 0,
            "aes_keys_used": 0,
        }
    
    def initialize(self, otp_bytes: int, aes_keys: int) -> None:
        """
        Initialize the key pool with pre-provisioned material.
        
        Args:
            otp_bytes: Number of bytes for OTP pool
            aes_keys: Number of AES keys to pre-generate
        """
        with self._lock:
            logger.info("Generating %d bytes of simulated QKD key material...", otp_bytes)
            self._otp_pool = bytearray(os.urandom(otp_bytes))
            self._otp_offset = 0
            
            self._aes_key_count = aes_keys
            
            logger.info("Key pool initialized (SIMULATION MODE)")
    
    def allocate_key(
        self,
        peer_id: str,
        size: int,
        key_type: str = "aes_seed",
    ) -> KeyEntry:
        """
        Allocate a new key from the pool.
        
        Args:
            peer_id: Identifier of the peer
            size: Requested key size in bytes
            key_type: Type of key (otp, aes_seed)
        
        Returns:
            KeyEntry with the allocated key
        
        Raises:
            ValueError: If insufficient key material
        """
        with self._lock:
            if key_type == "otp":
                available = len(self._otp_pool) - self._otp_offset
                if available < size:
                    raise ValueError(
                        f"Insufficient OTP key material. "
                        f"Requested: {size}, Available: {available}"
                    )
                
                key_material = bytes(
                    self._otp_pool[self._otp_offset:self._otp_offset + size]
                )
                self._otp_offset += size
                self._stats["otp_bytes_used"] += size
                
            else:
                if self._aes_key_count <= 0:
                    self._aes_key_count = 1000
                
                key_material = os.urandom(size)
                self._aes_key_count -= 1
                self._stats["aes_keys_used"] += 1
            
            key_id = str(uuid4())
            now = datetime.now(timezone.utc)
            
            entry = KeyEntry(
                key_id=key_id,
                key_material=key_material,
                peer_id=peer_id,
                key_type=key_type,
                created_at=now,
                expires_at=now + timedelta(days=1),
            )
            
            self._allocated_keys[key_id] = entry
            self._stats["total_allocated"] += 1
            
            return entry
    
    def get_key(self, key_id: str) -> Optional[KeyEntry]:
        """Get a key by ID without consuming it."""
        with self._lock:
            return self._allocated_keys.get(key_id)
    
    def consume_key(self, key_id: str) -> bool:
        """
        Mark a key as consumed (one-time use).
        
        Returns:
            True if successfully consumed
        """
        with self._lock:
            entry = self._allocated_keys.get(key_id)
            if entry is None:
                return False
            
            if entry.consumed:
                return False
            
            entry.consumed = True
            entry.consumed_at = datetime.now(timezone.utc)
            self._stats["total_consumed"] += 1
            
            for i in range(len(entry.key_material)):
                if isinstance(entry.key_material, bytearray):
                    entry.key_material[i] = 0
            
            return True
    
    def delete_key(self, key_id: str) -> bool:
        """Immediately delete a key."""
        with self._lock:
            entry = self._allocated_keys.pop(key_id, None)
            if entry:
                for i in range(len(entry.key_material)):
                    if isinstance(entry.key_material, bytearray):
                        entry.key_material[i] = 0
                return True
            return False
    
    def add_otp_material(self, size: int) -> None:
        """Add more OTP material to the pool."""
        with self._lock:
            new_material = os.urandom(size)
            self._otp_pool.extend(new_material)
            logger.info("Added %d bytes of OTP material", size)
    
    def add_aes_keys(self, count: int) -> None:
        """Add more AES key capacity."""
        with self._lock:
            self._aes_key_count += count
            logger.info("Added %d AES keys", count)
    
    def get_stats(self) -> dict:
        """Get pool statistics."""
        with self._lock:
            return {
                "otp_available": len(self._otp_pool) - self._otp_offset,
                "otp_total": len(self._otp_pool),
                "otp_used": self._otp_offset,
                "aes_available": self._aes_key_count,
                "total_allocated": self._stats["total_allocated"],
                "total_consumed": self._stats["total_consumed"],
            }
    
    def cleanup_expired(self) -> int:
        """Remove expired keys from the pool."""
        with self._lock:
            now = datetime.now(timezone.utc)
            expired = [
                key_id for key_id, entry in self._allocated_keys.items()
                if entry.expires_at and entry.expires_at < now
            ]
            
            for key_id in expired:
                self.delete_key(key_id)
            
            return len(expired)
