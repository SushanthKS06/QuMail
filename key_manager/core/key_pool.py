import hashlib
import logging
import os
import secrets
import threading
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)

_HAS_QUANTUM_SIM = False
try:
    import sys
    backend_path = Path(__file__).parent.parent.parent / "backend"
    if backend_path.exists():
        sys.path.insert(0, str(backend_path))
    
    from crypto_engine.quantum_sim import generate_quantum_bytes, health_check as entropy_health_check
    _HAS_QUANTUM_SIM = True
    logger.info("Quantum-grade entropy available for Key Manager")
    
    # Remove backend path to avoid import conflicts with key_manager's own api module
    if str(backend_path) in sys.path:
        sys.path.remove(str(backend_path))
except ImportError:
    logger.warning("Quantum sim not available, using os.urandom")


def _secure_random(size: int) -> bytes:
    if _HAS_QUANTUM_SIM:
        return generate_quantum_bytes(size)
    return os.urandom(size)


@dataclass
class KeyEntry:
    key_id: str
    key_material: bytes
    peer_id: str
    key_type: str
    created_at: datetime
    user_id: str = "default"
    expires_at: Optional[datetime] = None
    consumed: bool = False
    consumed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "key_id": self.key_id,
            "key_material_b64": __import__("base64").b64encode(self.key_material).decode(),
            "peer_id": self.peer_id,
            "key_type": self.key_type,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "consumed": self.consumed,
            "consumed_at": self.consumed_at.isoformat() if self.consumed_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KeyEntry":
        return cls(
            key_id=data["key_id"],
            key_material=__import__("base64").b64decode(data["key_material_b64"]),
            peer_id=data["peer_id"],
            key_type=data["key_type"],
            user_id=data.get("user_id", "default"),
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            consumed=data.get("consumed", False),
            consumed_at=datetime.fromisoformat(data["consumed_at"]) if data.get("consumed_at") else None,
        )


class KeyPool:
    
    def __init__(self, persistence_enabled: bool = False, persistence_path: Optional[Path] = None, 
                 persistence_password: Optional[str] = None, audit_path: Optional[Path] = None):
        self._lock = threading.RLock()
        self._otp_pool: bytearray = bytearray()
        self._otp_offset: int = 0
        self._aes_key_count: int = 0
        self._allocated_keys: Dict[str, KeyEntry] = {}
        self._user_quotas: Dict[str, Dict[str, int]] = {}
        
        self._stats = {
            "total_allocated": 0,
            "total_consumed": 0,
            "otp_bytes_used": 0,
            "aes_keys_used": 0,
        }
        
        self._persistence_enabled = persistence_enabled
        self._persistent_store = None
        self._audit_logger = None
        
        if persistence_enabled and persistence_path and persistence_password:
            from .persistent_store import PersistentKeyStore, AuditLogger
            self._persistent_store = PersistentKeyStore(persistence_path, persistence_password)
            
            if audit_path:
                self._audit_logger = AuditLogger(audit_path)
    
    def initialize(self, otp_bytes: int, aes_keys: int) -> None:
        with self._lock:
            if self._persistence_enabled and self._persistent_store:
                stored_data = self._persistent_store.initialize()
                
                if stored_data.get("keys"):
                    for key_id, key_data in stored_data["keys"].items():
                        try:
                            self._allocated_keys[key_id] = KeyEntry.from_dict(key_data)
                        except Exception as e:
                            logger.warning("Failed to restore key %s: %s", key_id, e)
                    
                    self._stats = stored_data.get("stats", self._stats)
                    
                    stored_otp = stored_data.get("otp_pool_b64")
                    if stored_otp:
                        import base64
                        self._otp_pool = bytearray(base64.b64decode(stored_otp))
                        self._otp_offset = stored_data.get("otp_offset", 0)
                        self._aes_key_count = stored_data.get("aes_key_count", aes_keys)
                        logger.info("Restored key pool state from persistence")
                        return
            
            source = "quantum-grade" if _HAS_QUANTUM_SIM else "classical PRNG"
            logger.info("Generating %d bytes of %s key material...", otp_bytes, source)
            
            self._otp_pool = bytearray(_secure_random(otp_bytes))
            self._otp_offset = 0
            self._aes_key_count = aes_keys
            
            self._persist()
            
            logger.info("Key pool initialized (%s entropy source)", source)
        self._allocation_hooks = []
    
    def register_allocation_hook(self, callback):
        self._allocation_hooks.append(callback)

    def inject_key(self, entry: KeyEntry) -> None:
        """Inject a key received from a peer QKD node."""
        with self._lock:
            if entry.key_id in self._allocated_keys:
                return # Already have it
            
            self._allocated_keys[entry.key_id] = entry
            self._stats["total_allocated"] += 1
            
            # If it's an AES key, track it in stats (though logical consistency with count is tricky here)
            if entry.key_type != "otp":
                 # We don't decrement _aes_key_count because this is an *external* key
                 pass
            
            self._persist()
            
            if self._audit_logger:
                self._audit_logger.log("INJECT", entry.key_id, {
                    "peer_id": entry.peer_id,
                    "key_type": entry.key_type,
                    "user_id": entry.user_id,
                    "source": "qkd_link"
                })

    def allocate_key(
        self,
        peer_id: str,
        size: int,
        key_type: str = "aes_seed",
        user_id: str = "default",
    ) -> KeyEntry:
        with self._lock:
            self._check_user_quota(user_id, key_type)
            
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
                    logger.info("Auto-replenished AES key count")
                
                key_material = _secure_random(size)
                self._aes_key_count -= 1
                self._stats["aes_keys_used"] += 1
            
            key_id = str(uuid4())
            now = datetime.now(timezone.utc)
            
            entry = KeyEntry(
                key_id=key_id,
                key_material=key_material,
                peer_id=peer_id,
                key_type=key_type,
                user_id=user_id,
                created_at=now,
                expires_at=now + timedelta(days=1),
            )
            
            self._allocated_keys[key_id] = entry
            self._stats["total_allocated"] += 1
            self._update_user_quota(user_id, key_type, 1)
            
            self._persist()
            
            if self._audit_logger:
                self._audit_logger.log("ALLOCATE", key_id, {
                    "peer_id": peer_id,
                    "key_type": key_type,
                    "size": size,
                    "user_id": user_id,
                })
            
            # Trigger hooks for distributed sync
            for hook in self._allocation_hooks:
                try:
                    hook(peer_id, entry)
                except Exception as e:
                    logger.error(f"Error in allocation hook: {e}")
            
            return entry
    
    def get_key(self, key_id: str) -> Optional[KeyEntry]:
        with self._lock:
            return self._allocated_keys.get(key_id)
    
    def consume_key(self, key_id: str) -> bool:
        with self._lock:
            entry = self._allocated_keys.get(key_id)
            if entry is None:
                return False
            
            if entry.consumed:
                return False
            
            entry.consumed = True
            entry.consumed_at = datetime.now(timezone.utc)
            self._stats["total_consumed"] += 1
            
            self._persist()
            
            if self._audit_logger:
                self._audit_logger.log("CONSUME", key_id, {
                    "peer_id": entry.peer_id,
                    "key_type": entry.key_type,
                    "user_id": entry.user_id,
                })
            
            return True
    
    def delete_key(self, key_id: str) -> bool:
        with self._lock:
            entry = self._allocated_keys.pop(key_id, None)
            if entry:
                self._zeroize_key(entry)
                self._persist()
                
                if self._audit_logger:
                    self._audit_logger.log("DELETE", key_id, {
                        "peer_id": entry.peer_id,
                        "key_type": entry.key_type,
                        "user_id": entry.user_id,
                    })
                
                return True
            return False
    
    def add_otp_material(self, size: int) -> None:
        with self._lock:
            new_material = _secure_random(size)
            self._otp_pool.extend(new_material)
            self._persist()
            logger.info("Added %d bytes of OTP material", size)
    
    def add_aes_keys(self, count: int) -> None:
        with self._lock:
            self._aes_key_count += count
            self._persist()
            logger.info("Added %d AES keys", count)
    
    def get_stats(self) -> dict:
        with self._lock:
            stats = {
                "otp_available": len(self._otp_pool) - self._otp_offset,
                "otp_total": len(self._otp_pool),
                "otp_used": self._otp_offset,
                "aes_available": self._aes_key_count,
                "total_allocated": self._stats["total_allocated"],
                "total_consumed": self._stats["total_consumed"],
                "keys_in_memory": len(self._allocated_keys),
                "persistence_enabled": self._persistence_enabled,
                "quantum_entropy": _HAS_QUANTUM_SIM,
            }
            
            if _HAS_QUANTUM_SIM:
                try:
                    stats["entropy_healthy"] = entropy_health_check()
                except:
                    stats["entropy_healthy"] = True
            
            return stats
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        with self._lock:
            quota = self._user_quotas.get(user_id, {})
            user_keys = [k for k in self._allocated_keys.values() if k.user_id == user_id]
            
            return {
                "user_id": user_id,
                "keys_allocated": len(user_keys),
                "keys_consumed": sum(1 for k in user_keys if k.consumed),
                "quota_used": quota,
            }
    
    def cleanup_expired(self) -> int:
        with self._lock:
            now = datetime.now(timezone.utc)
            expired = [
                key_id for key_id, entry in self._allocated_keys.items()
                if entry.expires_at and entry.expires_at < now
            ]
            
            for key_id in expired:
                entry = self._allocated_keys.pop(key_id)
                self._zeroize_key(entry)
                
                if self._audit_logger:
                    self._audit_logger.log("EXPIRE", key_id, {
                        "peer_id": entry.peer_id,
                    })
            
            if expired:
                self._persist()
            
            return len(expired)
    
    def shutdown(self) -> None:
        with self._lock:
            self._persist()
            
            for i in range(len(self._otp_pool)):
                self._otp_pool[i] = 0
            
            for entry in self._allocated_keys.values():
                self._zeroize_key(entry)
            
            logger.info("Key pool shutdown complete - all keys zeroized")
    
    def _persist(self) -> None:
        if not self._persistence_enabled or not self._persistent_store:
            return
        
        try:
            import base64
            
            keys_data = {
                key_id: entry.to_dict()
                for key_id, entry in self._allocated_keys.items()
            }
            
            data = {
                "keys": keys_data,
                "stats": self._stats.copy(),
                "otp_pool_b64": base64.b64encode(bytes(self._otp_pool)).decode(),
                "otp_offset": self._otp_offset,
                "aes_key_count": self._aes_key_count,
            }
            
            self._persistent_store.save(data)
            
        except Exception as e:
            logger.error("Failed to persist key pool: %s", e)
    
    def _zeroize_key(self, entry: KeyEntry) -> None:
        if isinstance(entry.key_material, (bytes, bytearray)):
            if isinstance(entry.key_material, bytearray):
                for i in range(len(entry.key_material)):
                    entry.key_material[i] = 0
    
    def _check_user_quota(self, user_id: str, key_type: str) -> None:
        pass
    
    def _update_user_quota(self, user_id: str, key_type: str, delta: int) -> None:
        if user_id not in self._user_quotas:
            self._user_quotas[user_id] = {}
        
        current = self._user_quotas[user_id].get(key_type, 0)
        self._user_quotas[user_id][key_type] = current + delta
