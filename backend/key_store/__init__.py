from .memory_store import MemoryKeyStore
from .encrypted_store import EncryptedKeyStore
from .lifecycle import KeyLifecycle

_memory_store = MemoryKeyStore()
_encrypted_store: EncryptedKeyStore | None = None
_lifecycle = KeyLifecycle()


async def get_private_key(key_type: str) -> bytes:
    key = _memory_store.get(f"private_{key_type}")
    if key:
        return key
    
    if _encrypted_store:
        key = await _encrypted_store.get(f"private_{key_type}")
        if key:
            _memory_store.store(f"private_{key_type}", key)
            return key
    
    from crypto_engine.pqc import generate_kyber_keypair
    
    public_key, private_key = generate_kyber_keypair()
    
    _memory_store.store(f"private_{key_type}", private_key)
    _memory_store.store(f"public_{key_type}", public_key)
    
    if _encrypted_store:
        await _encrypted_store.store(f"private_{key_type}", private_key)
        await _encrypted_store.store(f"public_{key_type}", public_key)
    
    return private_key


async def store_private_key(key_type: str, private_key: bytes, public_key: bytes = None) -> None:
    """Store a private key (and optionally paired public key) in both memory and encrypted storage."""
    _memory_store.store(f"private_{key_type}", private_key)
    
    if public_key:
        _memory_store.store(f"public_{key_type}", public_key)
    
    if _encrypted_store:
        await _encrypted_store.store(f"private_{key_type}", private_key)
        if public_key:
            await _encrypted_store.store(f"public_{key_type}", public_key)


async def get_public_key(key_type: str) -> bytes:
    key = _memory_store.get(f"public_{key_type}")
    if key:
        return key
    
    await get_private_key(key_type)
    
    return _memory_store.get(f"public_{key_type}") or b""


def store_session_key(key_id: str, key_material: bytes, key_type: str = "aes"):
    _memory_store.store(key_id, key_material, metadata={"type": key_type})
    _lifecycle.track(key_id, key_type)


def get_session_key(key_id: str) -> bytes | None:
    return _memory_store.get(key_id)


def consume_session_key(key_id: str) -> bytes | None:
    key = _memory_store.get(key_id)
    if key:
        _memory_store.remove(key_id)
        _lifecycle.mark_consumed(key_id)
    return key


async def initialize_store(encryption_key: bytes):
    global _encrypted_store
    from config import settings
    _encrypted_store = EncryptedKeyStore(settings.key_cache_path, encryption_key)
    await _encrypted_store.initialize()


__all__ = [
    "get_private_key",
    "store_private_key",
    "get_public_key",
    "store_session_key",
    "get_session_key",
    "consume_session_key",
    "initialize_store",
]
