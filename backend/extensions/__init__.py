"""
QuMail Extension Framework

This package provides the extension infrastructure for adding
secure communication features beyond email:
- Secure Chat
- Secure Voice/Video
- Secure File Transfer
"""

from .base import (
    ExtensionType,
    SecurityLevel,
    Message,
    EncryptedMessage,
    SecureExtension,
    ExtensionRegistry,
    get_extension_registry,
)

from .chat import SecureChatExtension, create_chat_extension
from .voice import SecureVoiceExtension, create_voice_extension

__all__ = [
    "ExtensionType",
    "SecurityLevel",
    "Message",
    "EncryptedMessage",
    "SecureExtension",
    "ExtensionRegistry",
    "get_extension_registry",
    "SecureChatExtension",
    "create_chat_extension",
    "SecureVoiceExtension",
    "create_voice_extension",
]
