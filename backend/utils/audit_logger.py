"""
Encryption Boundary Audit Logger for QuMail.

Provides structured logging for encryption/decryption boundary events
without ever leaking secret material (keys, plaintext, full ciphertext).

Only logs: timestamps, event types, partial key_ids, security levels,
data sizes, and hash prefixes.
"""

import logging
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MAX_AUDIT_ENTRIES = 500


@dataclass
class AuditEvent:
    """A single encryption boundary audit event."""
    timestamp: str
    event_type: str
    security_level: Optional[int] = None
    key_id: Optional[str] = None  # Only first 8 chars, never full key
    data_size: Optional[int] = None
    hash_prefix: Optional[str] = None  # Only first 12 chars of hash
    details: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        return {k: v for k, v in result.items() if v is not None}


class AuditLogger:
    """
    Ring-buffer audit logger for encryption boundary events.
    
    Security Invariants:
    - NEVER logs plaintext content
    - NEVER logs full encryption keys
    - NEVER logs full ciphertext
    - Only logs partial identifiers (first 8 chars of key_id, first 12 of hash)
    """

    def __init__(self, max_entries: int = MAX_AUDIT_ENTRIES):
        self._events: deque = deque(maxlen=max_entries)
        self._event_count = 0

    def log_event(
        self,
        event_type: str,
        *,
        security_level: Optional[int] = None,
        key_id: Optional[str] = None,
        data_size: Optional[int] = None,
        hash_prefix: Optional[str] = None,
        details: Optional[str] = None,
    ) -> None:
        """
        Log an encryption boundary event.
        
        Args:
            event_type: One of ENCRYPT_START, ENCRYPT_COMPLETE, DECRYPT_START,
                       DECRYPT_COMPLETE, INTEGRITY_CHECK_PASS, INTEGRITY_CHECK_FAIL,
                       TAMPERING_DETECTED.
            security_level: The encryption security level (1-4).
            key_id: Partial key identifier (truncated automatically).
            data_size: Size of data being processed in bytes.
            hash_prefix: First 12 chars of SHA-256 hash.
            details: Optional additional context (no secrets!).
        """
        # Truncate key_id to prevent leaking full identifiers
        safe_key_id = key_id[:8] + "..." if key_id and len(key_id) > 8 else key_id
        # Truncate hash prefix
        safe_hash = hash_prefix[:12] if hash_prefix else None

        event = AuditEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            security_level=security_level,
            key_id=safe_key_id,
            data_size=data_size,
            hash_prefix=safe_hash,
            details=details,
        )

        self._events.append(event)
        self._event_count += 1

        # Also emit to Python logging at appropriate levels
        log_msg = (
            f"[AUDIT] {event_type} | "
            f"level={security_level} | "
            f"key={safe_key_id or 'N/A'} | "
            f"size={data_size or 'N/A'} | "
            f"hash={safe_hash or 'N/A'}"
        )

        if "FAIL" in event_type or "TAMPER" in event_type:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

    def get_recent_events(self, count: int = 50) -> List[Dict[str, Any]]:
        """Return the most recent audit events as dicts."""
        events = list(self._events)
        return [e.to_dict() for e in events[-count:]]

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate audit statistics."""
        events = list(self._events)
        event_types: Dict[str, int] = {}
        for e in events:
            event_types[e.event_type] = event_types.get(e.event_type, 0) + 1

        return {
            "total_events": self._event_count,
            "buffer_size": len(events),
            "event_type_counts": event_types,
        }

    def clear(self) -> None:
        """Clear the audit log buffer."""
        self._events.clear()


# Singleton instance
audit_log = AuditLogger()
