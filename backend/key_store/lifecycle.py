import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class KeyState(Enum):
    PROVISIONED = "provisioned"
    RESERVED = "reserved"
    USED = "used"
    CONSUMED = "consumed"
    EXPIRED = "expired"
    ZEROIZED = "zeroized"


@dataclass
class KeyLifecycleEntry:
    key_id: str
    key_type: str
    state: KeyState
    created_at: datetime
    reserved_at: Optional[datetime] = None
    used_at: Optional[datetime] = None
    consumed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class KeyLifecycle:
    
    def __init__(self):
        self._entries: Dict[str, KeyLifecycleEntry] = {}
    
    def track(self, key_id: str, key_type: str) -> None:
        self._entries[key_id] = KeyLifecycleEntry(
            key_id=key_id,
            key_type=key_type,
            state=KeyState.PROVISIONED,
            created_at=datetime.now(timezone.utc),
        )
        logger.debug("Key %s: PROVISIONED (%s)", key_id, key_type)
    
    def reserve(self, key_id: str) -> bool:
        entry = self._entries.get(key_id)
        if not entry:
            return False
        
        if entry.state not in (KeyState.PROVISIONED,):
            logger.warning(
                "Cannot reserve key %s in state %s",
                key_id, entry.state.value
            )
            return False
        
        entry.state = KeyState.RESERVED
        entry.reserved_at = datetime.now(timezone.utc)
        logger.debug("Key %s: PROVISIONED → RESERVED", key_id)
        return True
    
    def mark_used(self, key_id: str) -> bool:
        entry = self._entries.get(key_id)
        if not entry:
            return False
        
        if entry.state not in (KeyState.RESERVED, KeyState.PROVISIONED):
            logger.warning(
                "Cannot mark key %s used in state %s",
                key_id, entry.state.value
            )
            return False
        
        entry.state = KeyState.USED
        entry.used_at = datetime.now(timezone.utc)
        logger.debug("Key %s: → USED", key_id)
        return True
    
    def mark_consumed(self, key_id: str) -> bool:
        entry = self._entries.get(key_id)
        if not entry:
            return False
        
        if entry.state == KeyState.CONSUMED:
            logger.warning("Key %s already consumed", key_id)
            return False
        
        entry.state = KeyState.CONSUMED
        entry.consumed_at = datetime.now(timezone.utc)
        logger.info("Key %s: → CONSUMED (one-time use complete)", key_id)
        return True
    
    def is_consumable(self, key_id: str) -> bool:
        entry = self._entries.get(key_id)
        if not entry:
            return True
        
        return entry.state not in (KeyState.CONSUMED, KeyState.ZEROIZED, KeyState.EXPIRED)
    
    def is_consumed(self, key_id: str) -> bool:
        entry = self._entries.get(key_id)
        if not entry:
            return False
        return entry.state == KeyState.CONSUMED
    
    def mark_zeroized(self, key_id: str) -> None:
        entry = self._entries.get(key_id)
        if entry:
            entry.state = KeyState.ZEROIZED
            logger.debug("Key %s: → ZEROIZED", key_id)
    
    def get_state(self, key_id: str) -> Optional[KeyState]:
        entry = self._entries.get(key_id)
        return entry.state if entry else None
    
    def cleanup_expired(self, max_age_seconds: int = 86400) -> int:
        now = datetime.now(timezone.utc)
        expired = []
        
        for key_id, entry in self._entries.items():
            age = (now - entry.created_at).total_seconds()
            if age > max_age_seconds:
                expired.append(key_id)
        
        for key_id in expired:
            del self._entries[key_id]
        
        if expired:
            logger.info("Cleaned up %d expired key entries", len(expired))
        
        return len(expired)
    
    def get_stats(self) -> Dict[str, int]:
        stats = {state.value: 0 for state in KeyState}
        for entry in self._entries.values():
            stats[entry.state.value] += 1
        return stats
