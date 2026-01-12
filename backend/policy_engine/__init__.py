"""
Policy Engine Package

Enforces security policies for email encryption.
Validates requests, checks capabilities, and handles fallbacks.
"""

from .validator import validate_send_request, check_recipient_capability
from .rules import SecurityRules
from .fallback import get_fallback_level

__all__ = [
    "validate_send_request",
    "check_recipient_capability",
    "SecurityRules",
    "get_fallback_level",
]
