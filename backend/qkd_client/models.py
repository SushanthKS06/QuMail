from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class KeyResponse:
    key_id: str
    key_material: bytes
    peer_id: str
    key_type: str
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    used: bool = False


@dataclass
class KeyStatusResponse:
    connected: bool
    otp_bytes_available: int
    aes_keys_available: int
    pqc_keys_available: int
    last_sync: Optional[datetime] = None
