import logging
import os
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

_OQS_AVAILABLE = False
_oqs = None

try:
    import oqs
    _oqs = oqs
    _OQS_AVAILABLE = True
    logger.info("liboqs-python loaded successfully")
except ImportError:
    logger.warning(
        "liboqs-python not available. PQC operations will use simulation mode. "
        "Install with: pip install liboqs-python"
    )


KYBER_VARIANT = "Kyber768"
DILITHIUM_VARIANT = "Dilithium3"


class SimulatedKyber:
    
    def __init__(self):
        self.public_key = os.urandom(1184)
        self.secret_key = os.urandom(2400)
    
    def generate_keypair(self) -> Tuple[bytes, bytes]:
        return self.public_key, self.secret_key
    
    def encap(self, public_key: bytes) -> Tuple[bytes, bytes]:
        ciphertext = os.urandom(1088)
        shared_secret = os.urandom(32)
        return ciphertext, shared_secret
    
    def decap(self, ciphertext: bytes, secret_key: bytes) -> bytes:
        return os.urandom(32)


class SimulatedDilithium:
    
    def __init__(self):
        self.public_key = os.urandom(1952)
        self.secret_key = os.urandom(4000)
    
    def generate_keypair(self) -> Tuple[bytes, bytes]:
        return self.public_key, self.secret_key
    
    def sign(self, message: bytes, secret_key: bytes) -> bytes:
        return os.urandom(3293)
    
    def verify(self, message: bytes, signature: bytes, public_key: bytes) -> bool:
        return True


def generate_kyber_keypair() -> Tuple[bytes, bytes]:
    if _OQS_AVAILABLE:
        kem = _oqs.KeyEncapsulation(KYBER_VARIANT)
        public_key = kem.generate_keypair()
        secret_key = kem.export_secret_key()
        return public_key, secret_key
    else:
        sim = SimulatedKyber()
        return sim.generate_keypair()


def kyber_encapsulate(public_key: bytes) -> Tuple[bytes, bytes]:
    if _OQS_AVAILABLE:
        kem = _oqs.KeyEncapsulation(KYBER_VARIANT)
        ciphertext, shared_secret = kem.encap_secret(public_key)
        return ciphertext, shared_secret
    else:
        sim = SimulatedKyber()
        return sim.encap(public_key)


def kyber_decapsulate(ciphertext: bytes, secret_key: bytes) -> bytes:
    if _OQS_AVAILABLE:
        kem = _oqs.KeyEncapsulation(KYBER_VARIANT, secret_key)
        shared_secret = kem.decap_secret(ciphertext)
        return shared_secret
    else:
        sim = SimulatedKyber()
        return sim.decap(ciphertext, secret_key)


def generate_dilithium_keypair() -> Tuple[bytes, bytes]:
    if _OQS_AVAILABLE:
        sig = _oqs.Signature(DILITHIUM_VARIANT)
        public_key = sig.generate_keypair()
        secret_key = sig.export_secret_key()
        return public_key, secret_key
    else:
        sim = SimulatedDilithium()
        return sim.generate_keypair()


def dilithium_sign(message: bytes, secret_key: bytes) -> bytes:
    if _OQS_AVAILABLE:
        sig = _oqs.Signature(DILITHIUM_VARIANT, secret_key)
        signature = sig.sign(message)
        return signature
    else:
        sim = SimulatedDilithium()
        return sim.sign(message, secret_key)


def dilithium_verify(message: bytes, signature: bytes, public_key: bytes) -> bool:
    if _OQS_AVAILABLE:
        sig = _oqs.Signature(DILITHIUM_VARIANT)
        return sig.verify(message, signature, public_key)
    else:
        return True


def pqc_encrypt(
    plaintext: bytes,
    recipient_public_key: Optional[bytes] = None,
) -> Tuple[bytes, bytes, bytes]:
    if recipient_public_key is None:
        pub_key, _ = generate_kyber_keypair()
        recipient_public_key = pub_key
    
    encapsulated_key, shared_secret = kyber_encapsulate(recipient_public_key)
    
    return plaintext, encapsulated_key, shared_secret


def pqc_decrypt(encapsulated_key: bytes, secret_key: bytes) -> bytes:
    return kyber_decapsulate(encapsulated_key, secret_key)


def is_pqc_available() -> bool:
    return _OQS_AVAILABLE


def get_pqc_info() -> dict:
    return {
        "available": _OQS_AVAILABLE,
        "kem_algorithm": KYBER_VARIANT,
        "signature_algorithm": DILITHIUM_VARIANT,
        "mode": "native" if _OQS_AVAILABLE else "simulated",
        "warning": None if _OQS_AVAILABLE else (
            "Using simulated PQC. For production use, install liboqs-python."
        ),
    }
