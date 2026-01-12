"""
In-Memory Key Store

Secure in-memory storage for session keys.
Keys are stored with automatic zeroization on removal.
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class KeyEntry:
    """Entry in the key store."""
    key_id: str
    key_material: bytearray
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    accessed_at: Optional[datetime] = None


class MemoryKeyStore:
    """
    Thread-safe in-memory key storage.
    
    Features:
    - Keys stored as mutable bytearrays for secure zeroization
    - Automatic cleanup of expired keys
    - Thread-safe access
    """
    
    def __init__(self, max_keys: int = 1000):
        self._store: Dict[str, KeyEntry] = {}
        self._lock = threading.RLock()
        self._max_keys = max_keys
    
    def store(
        self,
        key_id: str,
        key_material: bytes,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Store a key in memory.
        
        Args:
            key_id: Unique key identifier
            key_material: The key bytes
            metadata: Optional metadata about the key
        """
        with self._lock:
            if len(self._store) >= self._max_keys:
                self._evict_oldest()
            
            if key_id in self._store:
                self._zeroize_entry(self._store[key_id])
            
            self._store[key_id] = KeyEntry(
                key_id=key_id,
                key_material=bytearray(key_material),
                created_at=datetime.now(timezone.utc),
                metadata=metadata or {},
            )
    
    def get(self, key_id: str) -> Optional[bytes]:
        """
        Retrieve a key from memory.
        
        Args:
            key_id: Key to retrieve
        
        Returns:
            Key bytes or None if not found
        """
        with self._lock:
            entry = self._store.get(key_id)
            if entry:
                entry.accessed_at = datetime.now(timezone.utc)
                return bytes(entry.key_material)
            return None
    
    def remove(self, key_id: str) -> bool:
        """
        Remove and zeroize a key.
        
        Args:
            key_id: Key to remove
        
        Returns:
            True if key was found and removed
        """
        with self._lock:
            entry = self._store.pop(key_id, None)
            if entry:
                self._zeroize_entry(entry)
                return True
            return False
    
    def contains(self, key_id: str) -> bool:
        """Check if a key exists."""
        with self._lock:
            return key_id in self._store
    
    def clear(self) -> None:
        """Remove and zeroize all keys."""
        with self._lock:
            for entry in self._store.values():
                self._zeroize_entry(entry)
            self._store.clear()
    
    def count(self) -> int:
        """Get the number of stored keys."""
        with self._lock:
            return len(self._store)
    
    def _zeroize_entry(self, entry: KeyEntry) -> None:
        """Securely overwrite key material with zeros."""
        for i in range(len(entry.key_material)):
            entry.key_material[i] = 0
    
    def _evict_oldest(self) -> None:
        """Evict the oldest key to make room."""
        if not self._store:
            return
        
        oldest_id = min(
            self._store.keys(),
            key=lambda k: self._store[k].created_at
        )
        self.remove(oldest_id)
    
    def get_metadata(self, key_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a key without retrieving the key material."""
        with self._lock:
            entry = self._store.get(key_id)
            if entry:
                return entry.metadata.copy()
            return None
    
    def list_keys(self) -> list[str]:
        """List all key IDs (for debugging)."""
        with self._lock:
            return list(self._store.keys())
