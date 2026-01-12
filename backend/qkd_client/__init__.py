"""
QKD Client Package

Client for communicating with the Key Manager (KM) service.
Implements ETSI GS QKD 014-style REST API calls.
"""

from .client import (
    request_key,
    get_key,
    consume_key,
    get_key_status,
    request_key_refresh,
    KeyRequestError,
)

__all__ = [
    "request_key",
    "get_key",
    "consume_key",
    "get_key_status",
    "request_key_refresh",
    "KeyRequestError",
]
