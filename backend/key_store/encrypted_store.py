import base64
import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from crypto_engine.aes_gcm import aes_encrypt_combined, aes_decrypt_combined

logger = logging.getLogger(__name__)


PBKDF2_ITERATIONS = 480000
SALT_SIZE = 16


def derive_key_from_password(password: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
    """
    Derive an encryption key from a password using PBKDF2.
    
    Returns:
        Tuple of (derived_key, salt)
    """
    if salt is None:
        salt = os.urandom(SALT_SIZE)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    
    key = kdf.derive(password.encode("utf-8"))
    return key, salt


class EncryptedKeyStore:
    """
    Encrypted on-disk key storage with security hardening.
    
    Features:
    - AES-256-GCM encryption for stored keys
    - Secure zeroization of key material
    - Atomic file writes to prevent corruption
    - Thread-safe operations
    """
    
    def __init__(self, path: Path, encryption_key: bytes):
        self._path = path
        self._encryption_key = bytearray(encryption_key)
        self._cache: Dict[str, bytearray] = {}
        self._lock = threading.RLock()
        self._initialized = False
    
    async def initialize(self) -> None:
        with self._lock:
            if self._path.exists():
                try:
                    encrypted_data = self._path.read_bytes()
                    decrypted = aes_decrypt_combined(encrypted_data, bytes(self._encryption_key))
                    raw_cache = self._deserialize(decrypted)
                    self._cache = {k: bytearray(v) for k, v in raw_cache.items()}
                    logger.info("Loaded %d keys from encrypted store", len(self._cache))
                except Exception as e:
                    logger.warning("Failed to load encrypted store: %s", e)
                    self._cache = {}
            else:
                self._cache = {}
            
            self._initialized = True
    
    async def store(self, key_id: str, key_material: bytes, metadata: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            if not self._initialized:
                await self.initialize()
            
            if key_id in self._cache:
                self._zeroize(self._cache[key_id])
            
            self._cache[key_id] = bytearray(key_material)
            await self._persist()
    
    async def get(self, key_id: str) -> Optional[bytes]:
        with self._lock:
            if not self._initialized:
                await self.initialize()
            
            material = self._cache.get(key_id)
            if material:
                return bytes(material)
            return None
    
    async def remove(self, key_id: str) -> bool:
        with self._lock:
            if not self._initialized:
                await self.initialize()
            
            if key_id in self._cache:
                self._zeroize(self._cache[key_id])
                del self._cache[key_id]
                await self._persist()
                logger.info("Removed and zeroized key %s from encrypted store", key_id)
                return True
            return False
    
    async def list_keys(self) -> List[str]:
        with self._lock:
            if not self._initialized:
                await self.initialize()
            return list(self._cache.keys())
    
    async def clear(self) -> None:
        """Securely clear all stored keys."""
        with self._lock:
            for material in self._cache.values():
                self._zeroize(material)
            self._cache.clear()
            
            if self._path.exists():
                self._secure_delete(self._path)
            
            logger.info("Cleared encrypted key store")
    
    async def rotate_encryption_key(self, new_key: bytes) -> None:
        """Re-encrypt all stored keys with a new encryption key."""
        with self._lock:
            if not self._initialized:
                await self.initialize()
            
            self._zeroize(self._encryption_key)
            self._encryption_key = bytearray(new_key)
            
            await self._persist()
            logger.info("Rotated encryption key for key store")
    
    def __del__(self):
        """Ensure sensitive data is zeroized on destruction."""
        try:
            self._zeroize(self._encryption_key)
            for material in self._cache.values():
                self._zeroize(material)
        except:
            pass
    
    async def _persist(self) -> None:
        try:
            cache_bytes = {k: bytes(v) for k, v in self._cache.items()}
            serialized = self._serialize(cache_bytes)
            encrypted = aes_encrypt_combined(serialized, bytes(self._encryption_key))
            
            self._path.parent.mkdir(parents=True, exist_ok=True)
            
            temp_path = self._path.with_suffix(".tmp")
            temp_path.write_bytes(encrypted)
            temp_path.replace(self._path)
            
        except Exception as e:
            logger.error("Failed to persist encrypted store: %s", e)
            raise
    
    def _serialize(self, cache: Dict[str, bytes]) -> bytes:
        data = {k: base64.b64encode(v).decode() for k, v in cache.items()}
        return json.dumps(data).encode()
    
    def _deserialize(self, data: bytes) -> Dict[str, bytes]:
        parsed = json.loads(data.decode())
        return {k: base64.b64decode(v) for k, v in parsed.items()}
    
    def _zeroize(self, data: bytearray) -> None:
        """Securely overwrite sensitive data in memory."""
        for i in range(len(data)):
            data[i] = 0
    
    def _secure_delete(self, path: Path) -> None:
        """Attempt secure deletion by overwriting before unlinking."""
        try:
            size = path.stat().st_size
            with open(path, "wb") as f:
                f.write(os.urandom(size))
                f.flush()
                os.fsync(f.fileno())
            path.unlink()
        except Exception as e:
            logger.warning("Secure delete failed, falling back to regular delete: %s", e)
            try:
                path.unlink()
            except:
                pass
