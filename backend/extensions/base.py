"""
QuMail Extension Framework

This module provides the base classes for building secure communication extensions
that can leverage QuMail's quantum-secure encryption infrastructure.

Extensions can be built for:
- Secure Chat (text messaging)
- Secure Voice/Video calling
- Secure file transfer
- Other real-time communication protocols
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ExtensionType(Enum):
    CHAT = "chat"
    VOICE = "voice"
    VIDEO = "video"
    FILE_TRANSFER = "file_transfer"


class SecurityLevel(Enum):
    OTP = 1
    AES = 2
    PQC = 3
    NONE = 4


@dataclass
class Message:
    id: str
    sender: str
    recipient: str
    content: bytes
    timestamp: datetime
    security_level: SecurityLevel
    key_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EncryptedMessage:
    id: str
    sender: str
    recipient: str
    ciphertext: bytes
    key_id: str
    security_level: SecurityLevel
    nonce: Optional[bytes] = None
    tag: Optional[bytes] = None
    metadata: Optional[Dict[str, Any]] = None


class SecureExtension(ABC):
    """
    Abstract base class for secure communication extensions.
    
    All extensions must implement encryption and decryption methods
    that integrate with QuMail's QKD key infrastructure.
    """
    
    def __init__(self, extension_type: ExtensionType):
        self.extension_type = extension_type
        self._initialized = False
    
    @property
    def name(self) -> str:
        return f"QuMail-{self.extension_type.value.title()}"
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the extension and verify dependencies."""
        pass
    
    @abstractmethod
    async def encrypt_message(
        self,
        content: bytes,
        recipient: str,
        security_level: SecurityLevel = SecurityLevel.AES,
    ) -> EncryptedMessage:
        """
        Encrypt a message for the specified recipient.
        
        Args:
            content: The plaintext message content
            recipient: The recipient's identifier
            security_level: The desired security level
            
        Returns:
            An EncryptedMessage containing the ciphertext and metadata
        """
        pass
    
    @abstractmethod
    async def decrypt_message(
        self,
        encrypted: EncryptedMessage,
    ) -> Message:
        """
        Decrypt an encrypted message.
        
        Args:
            encrypted: The encrypted message to decrypt
            
        Returns:
            The decrypted Message
        """
        pass
    
    @abstractmethod
    async def get_peer_capabilities(
        self,
        peer_id: str,
    ) -> Dict[str, Any]:
        """
        Query the capabilities of a peer.
        
        Args:
            peer_id: The peer's identifier
            
        Returns:
            A dictionary of the peer's supported features and security levels
        """
        pass
    
    async def cleanup(self) -> None:
        """Cleanup resources when extension is unloaded."""
        self._initialized = False


class ExtensionRegistry:
    """Registry for managing loaded extensions."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._extensions = {}
        return cls._instance
    
    def register(self, extension: SecureExtension) -> None:
        """Register an extension."""
        key = extension.extension_type.value
        self._extensions[key] = extension
    
    def unregister(self, extension_type: ExtensionType) -> None:
        """Unregister an extension."""
        key = extension_type.value
        if key in self._extensions:
            del self._extensions[key]
    
    def get(self, extension_type: ExtensionType) -> Optional[SecureExtension]:
        """Get a registered extension by type."""
        return self._extensions.get(extension_type.value)
    
    def list_extensions(self) -> List[str]:
        """List all registered extension types."""
        return list(self._extensions.keys())
    
    async def initialize_all(self) -> None:
        """Initialize all registered extensions."""
        for ext in self._extensions.values():
            await ext.initialize()
    
    async def cleanup_all(self) -> None:
        """Cleanup all registered extensions."""
        for ext in self._extensions.values():
            await ext.cleanup()


def get_extension_registry() -> ExtensionRegistry:
    """Get the singleton extension registry."""
    return ExtensionRegistry()
