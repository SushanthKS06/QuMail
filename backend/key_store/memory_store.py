import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class KeyEntry:
    key_id: str
    key_material: bytearray
    created_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    accessed_at: Optional[datetime] = None


class MemoryKeyStore:
    
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
        with self._lock:
            entry = self._store.get(key_id)
            if entry:
                entry.accessed_at = datetime.now(timezone.utc)
                return bytes(entry.key_material)
            return None
    
    def remove(self, key_id: str) -> bool:
        with self._lock:
            entry = self._store.pop(key_id, None)
            if entry:
                self._zeroize_entry(entry)
                return True
            return False
    
    def contains(self, key_id: str) -> bool:
        with self._lock:
            return key_id in self._store
    
    def clear(self) -> None:
        with self._lock:
            for entry in self._store.values():
                self._zeroize_entry(entry)
            self._store.clear()
    
    def count(self) -> int:
        with self._lock:
            return len(self._store)
    
    def _zeroize_entry(self, entry: KeyEntry) -> None:
        for i in range(len(entry.key_material)):
            entry.key_material[i] = 0
    
    def _evict_oldest(self) -> None:
        if not self._store:
            return
        
        oldest_id = min(
            self._store.keys(),
            key=lambda k: self._store[k].created_at
        )
        self.remove(oldest_id)
    
    def get_metadata(self, key_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            entry = self._store.get(key_id)
            if entry:
                return entry.metadata.copy()
            return None
    
    def list_keys(self) -> list[str]:
        with self._lock:
            return list(self._store.keys())
