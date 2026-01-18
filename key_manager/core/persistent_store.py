import base64
import hashlib
import json
import logging
import os
import threading
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

PBKDF2_ITERATIONS = 480000
SALT_SIZE = 16
STORE_VERSION = 1


def _derive_key(password: str, salt: bytes) -> bytes:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


def _aes_encrypt(plaintext: bytes, key: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ciphertext


def _aes_decrypt(ciphertext: bytes, key: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    
    nonce = ciphertext[:12]
    ct = ciphertext[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ct, None)


class PersistentKeyStore:
    
    def __init__(self, path: Path, encryption_password: str):
        self._path = path
        self._lock = threading.RLock()
        self._salt: Optional[bytes] = None
        self._encryption_key: Optional[bytes] = None
        self._encryption_password = encryption_password
        self._initialized = False
    
    def initialize(self) -> Dict[str, Any]:
        with self._lock:
            if self._path.exists():
                return self._load()
            else:
                self._salt = os.urandom(SALT_SIZE)
                self._encryption_key = _derive_key(self._encryption_password, self._salt)
                self._initialized = True
                logger.info("Initialized new persistent key store")
                return {"keys": {}, "stats": {}, "version": STORE_VERSION}
    
    def _load(self) -> Dict[str, Any]:
        try:
            raw_data = self._path.read_bytes()
            
            self._salt = raw_data[:SALT_SIZE]
            encrypted_data = raw_data[SALT_SIZE:]
            
            self._encryption_key = _derive_key(self._encryption_password, self._salt)
            
            decrypted = _aes_decrypt(encrypted_data, self._encryption_key)
            data = json.loads(decrypted.decode("utf-8"))
            
            version = data.get("version", 0)
            if version < STORE_VERSION:
                data = self._migrate(data, version)
            
            self._initialized = True
            logger.info("Loaded %d keys from persistent store", len(data.get("keys", {})))
            return data
            
        except Exception as e:
            logger.error("Failed to load persistent store: %s", e)
            self._salt = os.urandom(SALT_SIZE)
            self._encryption_key = _derive_key(self._encryption_password, self._salt)
            self._initialized = True
            return {"keys": {}, "stats": {}, "version": STORE_VERSION}
    
    def save(self, data: Dict[str, Any]) -> None:
        with self._lock:
            if not self._initialized:
                raise RuntimeError("Store not initialized")
            
            data["version"] = STORE_VERSION
            data["saved_at"] = datetime.now(timezone.utc).isoformat()
            
            json_data = json.dumps(data, default=str).encode("utf-8")
            encrypted = _aes_encrypt(json_data, self._encryption_key)
            
            self._path.parent.mkdir(parents=True, exist_ok=True)
            
            temp_path = self._path.with_suffix(".tmp")
            temp_path.write_bytes(self._salt + encrypted)
            temp_path.replace(self._path)
            
            logger.debug("Saved persistent store with %d keys", len(data.get("keys", {})))
    
    def _migrate(self, data: Dict[str, Any], from_version: int) -> Dict[str, Any]:
        logger.info("Migrating store from version %d to %d", from_version, STORE_VERSION)
        
        data["version"] = STORE_VERSION
        return data
    
    def rotate_key(self, new_password: str) -> None:
        with self._lock:
            if not self._initialized:
                raise RuntimeError("Store not initialized")
            
            current_data = self._load() if self._path.exists() else {"keys": {}, "stats": {}}
            
            self._salt = os.urandom(SALT_SIZE)
            self._encryption_password = new_password
            self._encryption_key = _derive_key(new_password, self._salt)
            
            self.save(current_data)
            logger.info("Rotated encryption key for persistent store")
    
    def secure_delete(self) -> None:
        with self._lock:
            if self._path.exists():
                try:
                    size = self._path.stat().st_size
                    with open(self._path, "wb") as f:
                        f.write(os.urandom(size))
                        f.flush()
                        os.fsync(f.fileno())
                    self._path.unlink()
                    logger.info("Securely deleted persistent store")
                except Exception as e:
                    logger.warning("Secure delete failed: %s", e)
                    self._path.unlink(missing_ok=True)


class AuditLogger:
    
    def __init__(self, path: Path):
        self._path = path
        self._lock = threading.Lock()
        self._hash_chain: Optional[str] = None
        
        self._path.parent.mkdir(parents=True, exist_ok=True)
        
        if self._path.exists():
            try:
                lines = self._path.read_text().strip().split("\n")
                if lines:
                    last_entry = json.loads(lines[-1])
                    self._hash_chain = last_entry.get("hash")
            except:
                pass
        
        if self._hash_chain is None:
            self._hash_chain = hashlib.sha256(b"GENESIS").hexdigest()[:32]
    
    def log(self, action: str, key_id: str, details: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": action,
                "key_id": key_id,
                "details": details or {},
                "prev_hash": self._hash_chain,
            }
            
            entry_json = json.dumps(entry, sort_keys=True)
            entry["hash"] = hashlib.sha256(entry_json.encode()).hexdigest()[:32]
            self._hash_chain = entry["hash"]
            
            with open(self._path, "a") as f:
                f.write(json.dumps(entry) + "\n")
    
    def verify_chain(self) -> bool:
        if not self._path.exists():
            return True
        
        lines = self._path.read_text().strip().split("\n")
        prev_hash = hashlib.sha256(b"GENESIS").hexdigest()[:32]
        
        for line in lines:
            try:
                entry = json.loads(line)
                if entry.get("prev_hash") != prev_hash:
                    return False
                
                stored_hash = entry.pop("hash")
                entry_json = json.dumps(entry, sort_keys=True)
                expected_hash = hashlib.sha256(entry_json.encode()).hexdigest()[:32]
                
                if stored_hash != expected_hash:
                    return False
                
                prev_hash = stored_hash
                entry["hash"] = stored_hash
                
            except Exception:
                return False
        
        return True
    
    def get_entries(self, key_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        if not self._path.exists():
            return []
        
        lines = self._path.read_text().strip().split("\n")
        entries = []
        
        for line in reversed(lines):
            try:
                entry = json.loads(line)
                if key_id is None or entry.get("key_id") == key_id:
                    entries.append(entry)
                    if len(entries) >= limit:
                        break
            except:
                pass
        
        return entries
