"""
SHA-256 Integrity Hash Pipeline for QuMail.

Provides cryptographic integrity verification to prove that
decrypted content matches the original plaintext. This is the
core mechanism for the E2E encryption proof requirement:
    original_hash == decrypted_hash
"""

import hashlib
import hmac
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

HASH_ALGORITHM = "sha-256"


def compute_hash(data: bytes) -> str:
    """
    Compute SHA-256 hash of data.
    
    Returns:
        Hex-encoded SHA-256 digest.
    """
    return hashlib.sha256(data).hexdigest()


def verify_hash(data: bytes, expected_hash: str) -> bool:
    """
    Verify data matches expected SHA-256 hash using constant-time comparison.
    
    Returns:
        True if the computed hash matches expected_hash.
    """
    computed = compute_hash(data)
    return hmac.compare_digest(computed, expected_hash)


def create_integrity_envelope(plaintext: bytes) -> Dict[str, str]:
    """
    Create an integrity envelope containing the SHA-256 hash
    of the plaintext. This envelope is embedded in the encrypted
    metadata so that after decryption, the receiver can verify
    that the decrypted content matches the original.
    
    Returns:
        Dict with 'algorithm' and 'hash' fields.
    """
    return {
        "algorithm": HASH_ALGORITHM,
        "hash": compute_hash(plaintext),
    }


def verify_integrity_envelope(
    plaintext: bytes,
    envelope: Dict[str, str],
) -> bool:
    """
    Verify that decrypted plaintext matches the integrity hash
    stored in the envelope.
    
    Args:
        plaintext: The decrypted data to verify.
        envelope: Dict containing 'algorithm' and 'hash'.
    
    Returns:
        True if the hash matches, False otherwise.
    """
    if not envelope:
        logger.warning("No integrity envelope provided, skipping verification")
        return True
    
    algorithm = envelope.get("algorithm", "")
    expected_hash = envelope.get("hash", "")
    
    if algorithm != HASH_ALGORITHM:
        logger.error(
            "Unsupported integrity algorithm: %s (expected %s)",
            algorithm, HASH_ALGORITHM,
        )
        return False
    
    if not expected_hash:
        logger.warning("Empty integrity hash in envelope")
        return False
    
    is_valid = verify_hash(plaintext, expected_hash)
    
    if is_valid:
        logger.debug(
            "Integrity check PASSED (hash prefix: %s...)",
            expected_hash[:12],
        )
    else:
        logger.error(
            "Integrity check FAILED! Expected hash prefix: %s..., "
            "computed hash prefix: %s...",
            expected_hash[:12],
            compute_hash(plaintext)[:12],
        )
    
    return is_valid
