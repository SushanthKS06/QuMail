"""
QuMail Secure Chat Extension

Provides end-to-end encrypted chat messaging using QuMail's
quantum-secure key infrastructure.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .base import (
    ExtensionType,
    EncryptedMessage,
    Message,
    SecureExtension,
    SecurityLevel,
)

logger = logging.getLogger(__name__)


class ChatSession:
    """Represents an active chat session with a peer."""
    
    def __init__(self, peer_id: str, security_level: SecurityLevel = SecurityLevel.AES):
        self.id = str(uuid4())
        self.peer_id = peer_id
        self.security_level = security_level
        self.created_at = datetime.now(timezone.utc)
        self.messages: List[Message] = []
        self.is_active = True
    
    def add_message(self, message: Message) -> None:
        self.messages.append(message)
    
    def close(self) -> None:
        self.is_active = False


class SecureChatExtension(SecureExtension):
    """
    Secure chat extension for QuMail.
    
    Features:
    - End-to-end encryption using OTP, AES, or PQC
    - Session management
    - Message history (in-memory)
    - Peer capability discovery
    """
    
    def __init__(self):
        super().__init__(ExtensionType.CHAT)
        self._sessions: Dict[str, ChatSession] = {}
        self._message_queue: List[EncryptedMessage] = []
    
    async def initialize(self) -> None:
        logger.info("Initializing SecureChatExtension...")
        self._initialized = True
        logger.info("SecureChatExtension initialized successfully")
    
    async def encrypt_message(
        self,
        content: bytes,
        recipient: str,
        security_level: SecurityLevel = SecurityLevel.AES,
    ) -> EncryptedMessage:
        from crypto_engine import encrypt_email
        from qkd_client import request_key
        
        if security_level == SecurityLevel.NONE:
            return EncryptedMessage(
                id=str(uuid4()),
                sender="self",
                recipient=recipient,
                ciphertext=content,
                key_id="",
                security_level=security_level,
            )
        
        result = await encrypt_email(
            body=content.decode("utf-8"),
            security_level=security_level.value,
            recipients=[recipient],
        )
        
        return EncryptedMessage(
            id=str(uuid4()),
            sender="self",
            recipient=recipient,
            ciphertext=result["ciphertext"].encode("utf-8"),
            key_id=result.get("key_id", ""),
            security_level=security_level,
            metadata=result.get("metadata"),
        )
    
    async def decrypt_message(
        self,
        encrypted: EncryptedMessage,
    ) -> Message:
        from crypto_engine import decrypt_email
        
        if encrypted.security_level == SecurityLevel.NONE:
            return Message(
                id=encrypted.id,
                sender=encrypted.sender,
                recipient=encrypted.recipient,
                content=encrypted.ciphertext,
                timestamp=datetime.now(timezone.utc),
                security_level=encrypted.security_level,
            )
        
        email_data = {
            "encrypted_body": encrypted.ciphertext.decode("utf-8"),
            "security_level": encrypted.security_level.value,
            "key_id": encrypted.key_id,
            "encryption_metadata": encrypted.metadata or {},
        }
        
        result = await decrypt_email(email_data)
        
        return Message(
            id=encrypted.id,
            sender=encrypted.sender,
            recipient=encrypted.recipient,
            content=result["body"].encode("utf-8"),
            timestamp=datetime.now(timezone.utc),
            security_level=encrypted.security_level,
            key_id=encrypted.key_id,
        )
    
    async def get_peer_capabilities(
        self,
        peer_id: str,
    ) -> Dict[str, Any]:
        from storage.database import get_known_recipient
        
        recipient = await get_known_recipient(peer_id)
        
        if recipient:
            return {
                "peer_id": peer_id,
                "is_qumail_user": recipient.get("is_qumail_user", False),
                "supported_levels": recipient.get("supported_levels", [4]),
                "supports_chat": True,
                "supports_voice": False,
                "supports_video": False,
            }
        
        return {
            "peer_id": peer_id,
            "is_qumail_user": False,
            "supported_levels": [4],
            "supports_chat": False,
            "supports_voice": False,
            "supports_video": False,
        }
    
    def create_session(
        self,
        peer_id: str,
        security_level: SecurityLevel = SecurityLevel.AES,
    ) -> ChatSession:
        session = ChatSession(peer_id, security_level)
        self._sessions[session.id] = session
        logger.info("Created chat session %s with peer %s", session.id, peer_id)
        return session
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        return self._sessions.get(session_id)
    
    def close_session(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.close()
            logger.info("Closed chat session %s", session_id)
    
    def list_active_sessions(self) -> List[ChatSession]:
        return [s for s in self._sessions.values() if s.is_active]
    
    async def cleanup(self) -> None:
        for session_id in list(self._sessions.keys()):
            self.close_session(session_id)
        self._sessions.clear()
        self._message_queue.clear()
        await super().cleanup()


def create_chat_extension() -> SecureChatExtension:
    """Factory function to create a chat extension instance."""
    return SecureChatExtension()
