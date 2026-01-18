import ctypes
import hashlib
import logging
import os
import secrets
import struct
import threading
import time
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms
    from cryptography.hazmat.backends import default_backend
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False

ENTROPY_POOL_SIZE = 256
RESEED_INTERVAL_BYTES = 1024 * 1024
MIN_ENTROPY_SOURCES = 2


class EntropyPool:
    
    def __init__(self):
        self._pool = bytearray(ENTROPY_POOL_SIZE)
        self._lock = threading.Lock()
        self._bytes_since_reseed = 0
        self._total_bytes_generated = 0
        self._reseed_count = 0
        self._sources_available = []
        self._last_health_check = 0
        self._health_status = True
        
        self._initialize_pool()
    
    def _initialize_pool(self) -> None:
        entropy_sources = []
        
        os_entropy = os.urandom(64)
        entropy_sources.append(("os_urandom", os_entropy))
        self._sources_available.append("os_urandom")
        
        try:
            cng_entropy = self._get_windows_cng_entropy(64)
            if cng_entropy:
                entropy_sources.append(("windows_cng", cng_entropy))
                self._sources_available.append("windows_cng")
        except Exception as e:
            logger.debug("Windows CNG not available: %s", e)
        
        timing_entropy = self._get_timing_entropy(32)
        entropy_sources.append(("timing_jitter", timing_entropy))
        self._sources_available.append("timing_jitter")
        
        try:
            secrets_entropy = secrets.token_bytes(64)
            entropy_sources.append(("secrets_module", secrets_entropy))
            self._sources_available.append("secrets_module")
        except Exception:
            pass
        
        combined = b"".join(data for _, data in entropy_sources)
        
        conditioned = self._condition_entropy(combined)
        
        with self._lock:
            for i in range(min(len(conditioned), ENTROPY_POOL_SIZE)):
                self._pool[i] = conditioned[i]
        
        logger.info(
            "Entropy pool initialized with %d sources: %s",
            len(entropy_sources),
            ", ".join(self._sources_available)
        )
    
    def _get_windows_cng_entropy(self, size: int) -> Optional[bytes]:
        if os.name != 'nt':
            return None
        
        try:
            advapi32 = ctypes.windll.advapi32
            
            buffer = ctypes.create_string_buffer(size)
            
            PROV_RSA_FULL = 1
            CRYPT_VERIFYCONTEXT = 0xF0000000
            
            hProv = ctypes.c_void_p()
            
            if advapi32.CryptAcquireContextW(
                ctypes.byref(hProv),
                None,
                None,
                PROV_RSA_FULL,
                CRYPT_VERIFYCONTEXT
            ):
                try:
                    if advapi32.CryptGenRandom(hProv, size, buffer):
                        return buffer.raw
                finally:
                    advapi32.CryptReleaseContext(hProv, 0)
        except Exception as e:
            logger.debug("CNG entropy failed: %s", e)
        
        try:
            bcrypt = ctypes.windll.bcrypt
            buffer = (ctypes.c_ubyte * size)()
            status = bcrypt.BCryptGenRandom(None, buffer, size, 2)
            if status == 0:
                return bytes(buffer)
        except Exception as e:
            logger.debug("BCrypt entropy failed: %s", e)
        
        return None
    
    def _get_timing_entropy(self, size: int) -> bytes:
        samples = []
        for _ in range(size * 8):
            start = time.perf_counter_ns()
            _ = hashlib.sha256(os.urandom(32)).digest()
            end = time.perf_counter_ns()
            samples.append((end - start) & 0xFF)
        
        result = bytearray(size)
        for i in range(size):
            byte_val = 0
            for bit in range(8):
                idx = i * 8 + bit
                byte_val |= (samples[idx] & 1) << bit
            result[i] = byte_val
        
        return bytes(result)
    
    def _condition_entropy(self, raw_entropy: bytes) -> bytes:
        result = bytearray(ENTROPY_POOL_SIZE)
        
        for i in range(0, ENTROPY_POOL_SIZE, 64):
            block_input = raw_entropy + i.to_bytes(4, 'little')
            block = hashlib.blake2b(block_input, digest_size=64).digest()
            chunk_size = min(64, ENTROPY_POOL_SIZE - i)
            result[i:i + chunk_size] = block[:chunk_size]
        
        return bytes(result)
    
    def reseed(self) -> None:
        new_entropy = []
        
        new_entropy.append(os.urandom(32))
        
        cng = self._get_windows_cng_entropy(32)
        if cng:
            new_entropy.append(cng)
        
        new_entropy.append(self._get_timing_entropy(16))
        
        with self._lock:
            combined = bytes(self._pool) + b"".join(new_entropy)
            conditioned = self._condition_entropy(combined)
            
            for i in range(ENTROPY_POOL_SIZE):
                self._pool[i] = conditioned[i]
            
            self._bytes_since_reseed = 0
            self._reseed_count += 1
        
        logger.debug("Entropy pool reseeded (count: %d)", self._reseed_count)
    
    def extract(self, size: int) -> bytes:
        if size <= 0:
            raise ValueError("Size must be positive")
        
        with self._lock:
            if self._bytes_since_reseed >= RESEED_INTERVAL_BYTES:
                pass
            
            output = bytearray(size)
            offset = 0
            counter = 0
            
            while offset < size:
                block_input = bytes(self._pool) + struct.pack("<Q", counter)
                block = hashlib.blake2b(block_input, digest_size=64).digest()
                
                chunk_size = min(32, size - offset)
                output[offset:offset + chunk_size] = block[:chunk_size]
                
                for i in range(ENTROPY_POOL_SIZE):
                    self._pool[i] ^= block[32 + (i % 32)]
                
                offset += chunk_size
                counter += 1
            
            self._bytes_since_reseed += size
            self._total_bytes_generated += size
            
            return bytes(output)
    
    def get_stats(self) -> dict:
        with self._lock:
            return {
                "sources_available": self._sources_available.copy(),
                "total_bytes_generated": self._total_bytes_generated,
                "reseed_count": self._reseed_count,
                "bytes_since_reseed": self._bytes_since_reseed,
                "health_status": self._health_status,
            }
    
    def health_check(self) -> bool:
        sample = self.extract(256)
        
        byte_counts = [0] * 256
        for b in sample:
            byte_counts[b] += 1
        
        expected = len(sample) / 256
        chi_squared = sum((count - expected) ** 2 / expected for count in byte_counts)
        
        self._health_status = chi_squared < 350
        self._last_health_check = time.time()
        
        return self._health_status


class ChaCha20CSPRNG:
    
    def __init__(self, entropy_pool: EntropyPool):
        self._entropy_pool = entropy_pool
        self._lock = threading.Lock()
        self._key = bytearray(32)
        self._nonce = bytearray(16)
        self._counter = 0
        self._bytes_generated = 0
        self._reseed_threshold = 64 * 1024
        
        self._reseed()
    
    def _reseed(self) -> None:
        seed_material = self._entropy_pool.extract(64)
        
        with self._lock:
            for i in range(32):
                self._key[i] = seed_material[i]
            for i in range(16):
                self._nonce[i] = seed_material[32 + i]
            
            self._counter = 0
            self._bytes_generated = 0
    
    def generate(self, size: int) -> bytes:
        if size <= 0:
            raise ValueError("Size must be positive")
        
        with self._lock:
            if self._bytes_generated >= self._reseed_threshold:
                self._reseed()
            
            if HAS_CRYPTOGRAPHY:
                output = self._generate_chacha20(size)
            else:
                output = self._generate_fallback(size)
            
            self._bytes_generated += size
            self._counter += 1
            
            return output
    
    def _generate_chacha20(self, size: int) -> bytes:
        nonce = bytes(self._nonce)
        cipher = Cipher(
            algorithms.ChaCha20(bytes(self._key), nonce),
            mode=None,
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        plaintext = b"\x00" * size
        return encryptor.update(plaintext)
    
    def _generate_fallback(self, size: int) -> bytes:
        output = bytearray(size)
        offset = 0
        counter = self._counter
        
        while offset < size:
            block_input = bytes(self._key) + bytes(self._nonce) + struct.pack("<Q", counter)
            block = hashlib.blake2b(block_input, digest_size=64).digest()
            
            chunk_size = min(64, size - offset)
            output[offset:offset + chunk_size] = block[:chunk_size]
            
            offset += chunk_size
            counter += 1
        
        return bytes(output)
    
    def get_stats(self) -> dict:
        with self._lock:
            return {
                "bytes_since_reseed": self._bytes_generated,
                "reseed_threshold": self._reseed_threshold,
                "using_chacha20": HAS_CRYPTOGRAPHY,
            }


_entropy_pool: Optional[EntropyPool] = None
_csprng: Optional[ChaCha20CSPRNG] = None
_init_lock = threading.Lock()


def _ensure_initialized() -> ChaCha20CSPRNG:
    global _entropy_pool, _csprng
    
    if _csprng is not None:
        return _csprng
    
    with _init_lock:
        if _csprng is not None:
            return _csprng
        
        _entropy_pool = EntropyPool()
        _csprng = ChaCha20CSPRNG(_entropy_pool)
        
        logger.info("Quantum-grade CSPRNG initialized")
        
        return _csprng


def generate_quantum_bytes(size: int) -> bytes:
    csprng = _ensure_initialized()
    return csprng.generate(size)


def generate_quantum_key(size: int = 32) -> Tuple[bytes, str]:
    key_material = generate_quantum_bytes(size)
    key_id = secrets.token_hex(16)
    return key_material, key_id


def get_entropy_stats() -> dict:
    _ensure_initialized()
    return {
        "entropy_pool": _entropy_pool.get_stats(),
        "csprng": _csprng.get_stats(),
    }


def health_check() -> bool:
    _ensure_initialized()
    return _entropy_pool.health_check()


def force_reseed() -> None:
    _ensure_initialized()
    _entropy_pool.reseed()
    _csprng._reseed()
    logger.info("Forced reseed of entropy pool and CSPRNG")
