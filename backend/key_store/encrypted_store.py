"""
Encrypted Disk Key Store

Persistent key storage with AES encryption.
Keys are never stored in plaintext on disk.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from crypto_engine.aes_gcm import aes_encrypt_combined, aes_decrypt_combined

logger = logging.getLogger(__name__)


class EncryptedKeyStore:
    """
    Encrypted persistent key storage.
    
    Keys are encrypted with AES-256-GCM before writing to disk.
    The encryption key should be derived from a master secret
    that is stored securely (e.g., in OS keychain).
    """
    
    def __init__(self, path: Path, encryption_key: bytes):
        """
        Initialize the encrypted store.
        
        Args:
            path: Path to the encrypted key file
            encryption_key: 32-byte AES key for encryption
        """
        self._path = path
        self._encryption_key = encryption_key
        self._cache: Dict[str, bytes] = {}
        self._initialized = False
    
    async def initialize(self) -> None:
        """Load existing keys from disk."""
        if self._path.exists():
            try:
                encrypted_data = self._path.read_bytes()
                decrypted = aes_decrypt_combined(encrypted_data, self._encryption_key)
                self._cache = self._deserialize(decrypted)
                logger.info("Loaded %d keys from encrypted store", len(self._cache))
            except Exception as e:
                logger.warning("Failed to load encrypted store: %s", e)
                self._cache = {}
        else:
            self._cache = {}
        
        self._initialized = True
    
    async def store(self, key_id: str, key_material: bytes) -> None:
        """
        Store a key encrypted on disk.
        
        Args:
            key_id: Unique key identifier
            key_material: Key bytes to store
        """
        if not self._initialized:
            await self.initialize()
        
        self._cache[key_id] = key_material
        await self._persist()
    
    async def get(self, key_id: str) -> Optional[bytes]:
        """
        Retrieve a key from the encrypted store.
        
        Args:
            key_id: Key to retrieve
        
        Returns:
            Key bytes or None if not found
        """
        if not self._initialized:
            await self.initialize()
        
        return self._cache.get(key_id)
    
    async def remove(self, key_id: str) -> bool:
        """
        Remove a key from the store.
        
        Args:
            key_id: Key to remove
        
        Returns:
            True if key was found and removed
        """
        if not self._initialized:
            await self.initialize()
        
        if key_id in self._cache:
            del self._cache[key_id]
            await self._persist()
            return True
        return False
    
    async def list_keys(self) -> list[str]:
        """List all stored key IDs."""
        if not self._initialized:
            await self.initialize()
        return list(self._cache.keys())
    
    async def _persist(self) -> None:
        """Write all keys encrypted to disk."""
        try:
            serialized = self._serialize(self._cache)
            encrypted = aes_encrypt_combined(serialized, self._encryption_key)
            
            self._path.parent.mkdir(parents=True, exist_ok=True)
            
            temp_path = self._path.with_suffix(".tmp")
            temp_path.write_bytes(encrypted)
            temp_path.replace(self._path)
            
        except Exception as e:
            logger.error("Failed to persist encrypted store: %s", e)
            raise
    
    def _serialize(self, cache: Dict[str, bytes]) -> bytes:
        """Serialize the cache to bytes."""
        import base64
        data = {k: base64.b64encode(v).decode() for k, v in cache.items()}
        return json.dumps(data).encode()
    
    def _deserialize(self, data: bytes) -> Dict[str, bytes]:
        """Deserialize bytes to cache dict."""
        import base64
        parsed = json.loads(data.decode())
        return {k: base64.b64decode(v) for k, v in parsed.items()}
