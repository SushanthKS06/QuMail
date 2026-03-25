"""
Test suite for SHA-256 integrity hash pipeline.
"""

import os
import pytest
from crypto_engine.integrity import (
    compute_hash,
    verify_hash,
    create_integrity_envelope,
    verify_integrity_envelope,
    HASH_ALGORITHM,
)


class TestComputeHash:

    def test_deterministic(self):
        """Same input always produces the same hash."""
        data = b"Hello, QuMail!"
        h1 = compute_hash(data)
        h2 = compute_hash(data)
        assert h1 == h2

    def test_different_inputs_different_hashes(self):
        """Different inputs produce different hashes."""
        h1 = compute_hash(b"message A")
        h2 = compute_hash(b"message B")
        assert h1 != h2

    def test_empty_input(self):
        """Empty input should still produce a valid 64-char hex hash."""
        h = compute_hash(b"")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_large_input(self):
        """Large inputs should produce a 64-char hash."""
        data = os.urandom(1_000_000)
        h = compute_hash(data)
        assert len(h) == 64

    def test_hash_is_hex(self):
        """Hash should be a hex string."""
        h = compute_hash(b"test data")
        int(h, 16)  # Should not raise


class TestVerifyHash:

    def test_correct_hash_passes(self):
        data = b"This message is authentic."
        h = compute_hash(data)
        assert verify_hash(data, h) is True

    def test_incorrect_hash_fails(self):
        data = b"This message is authentic."
        fake_hash = "a" * 64
        assert verify_hash(data, fake_hash) is False

    def test_modified_data_fails(self):
        original = b"original message"
        h = compute_hash(original)
        tampered = b"tampered message"
        assert verify_hash(tampered, h) is False

    def test_single_bit_change_fails(self):
        data = bytearray(b"exact message")
        h = compute_hash(bytes(data))
        data[0] ^= 0x01  # Flip one bit
        assert verify_hash(bytes(data), h) is False


class TestIntegrityEnvelope:

    def test_create_envelope_has_required_fields(self):
        envelope = create_integrity_envelope(b"test")
        assert "algorithm" in envelope
        assert "hash" in envelope
        assert envelope["algorithm"] == HASH_ALGORITHM

    def test_envelope_hash_matches_computed(self):
        data = b"verify me"
        envelope = create_integrity_envelope(data)
        assert envelope["hash"] == compute_hash(data)

    def test_verify_valid_envelope(self):
        data = b"authentic message"
        envelope = create_integrity_envelope(data)
        assert verify_integrity_envelope(data, envelope) is True

    def test_verify_tampered_data_fails(self):
        original = b"authentic message"
        envelope = create_integrity_envelope(original)
        tampered = b"tampered message"
        assert verify_integrity_envelope(tampered, envelope) is False

    def test_verify_empty_envelope_returns_true(self):
        """Empty envelope should return True (skip verification)."""
        assert verify_integrity_envelope(b"data", {}) is True

    def test_verify_wrong_algorithm_fails(self):
        envelope = {"algorithm": "md5", "hash": "abc123"}
        assert verify_integrity_envelope(b"data", envelope) is False

    def test_verify_empty_hash_fails(self):
        envelope = {"algorithm": HASH_ALGORITHM, "hash": ""}
        assert verify_integrity_envelope(b"data", envelope) is False
