import pytest
from crypto_engine.pqc import (
    generate_kyber_keypair,
    kyber_encapsulate,
    kyber_decapsulate,
    generate_dilithium_keypair,
    dilithium_sign,
    dilithium_verify,
    pqc_encrypt,
    pqc_decrypt,
    is_pqc_available,
    get_pqc_info,
    SimulatedKyber,
    SimulatedDilithium,
)


class TestKyberKeyGeneration:
    
    def test_generate_keypair_returns_tuple(self):
        result = generate_kyber_keypair()
        assert isinstance(result, tuple)
        assert len(result) == 2
    
    def test_generate_keypair_returns_bytes(self):
        public_key, secret_key = generate_kyber_keypair()
        assert isinstance(public_key, bytes)
        assert isinstance(secret_key, bytes)
    
    def test_public_key_has_expected_length(self):
        public_key, _ = generate_kyber_keypair()
        assert len(public_key) >= 800
    
    def test_secret_key_has_expected_length(self):
        _, secret_key = generate_kyber_keypair()
        assert len(secret_key) >= 1600
    
    def test_keypairs_are_unique(self):
        pairs = [generate_kyber_keypair() for _ in range(10)]
        public_keys = [p[0] for p in pairs]
        assert len(set(public_keys)) == 10


class TestKyberEncapsulation:
    
    def test_encapsulate_returns_tuple(self):
        public_key, _ = generate_kyber_keypair()
        result = kyber_encapsulate(public_key)
        assert isinstance(result, tuple)
        assert len(result) == 2
    
    def test_encapsulate_returns_ciphertext_and_secret(self):
        public_key, _ = generate_kyber_keypair()
        ciphertext, shared_secret = kyber_encapsulate(public_key)
        assert isinstance(ciphertext, bytes)
        assert isinstance(shared_secret, bytes)
    
    def test_shared_secret_is_32_bytes(self):
        public_key, _ = generate_kyber_keypair()
        _, shared_secret = kyber_encapsulate(public_key)
        assert len(shared_secret) == 32
    
    def test_encapsulation_decapsulation_consistency(self):
        sim = SimulatedKyber()
        public_key, secret_key = sim.generate_keypair()
        ciphertext, encap_secret = sim.encap(public_key)
        decap_secret = sim.decap(ciphertext, secret_key)
        assert encap_secret == decap_secret


class TestKyberDecapsulation:
    
    def test_simulated_decap_returns_cached_secret(self):
        sim = SimulatedKyber()
        public_key, secret_key = sim.generate_keypair()
        ciphertext, shared_secret = sim.encap(public_key)
        decap_secret = sim.decap(ciphertext, secret_key)
        assert decap_secret == shared_secret
    
    def test_simulated_decap_unknown_ciphertext_uses_fallback(self):
        import os
        sim = SimulatedKyber()
        _, secret_key = sim.generate_keypair()
        unknown_ciphertext = os.urandom(1088)
        result1 = sim.decap(unknown_ciphertext, secret_key)
        result2 = sim.decap(unknown_ciphertext, secret_key)
        assert result1 == result2


class TestDilithiumKeyGeneration:
    
    def test_generate_keypair_returns_tuple(self):
        result = generate_dilithium_keypair()
        assert isinstance(result, tuple)
        assert len(result) == 2
    
    def test_generate_keypair_returns_bytes(self):
        public_key, secret_key = generate_dilithium_keypair()
        assert isinstance(public_key, bytes)
        assert isinstance(secret_key, bytes)


class TestDilithiumSignature:
    
    def test_sign_returns_bytes(self):
        _, secret_key = generate_dilithium_keypair()
        message = b"test message"
        signature = dilithium_sign(message, secret_key)
        assert isinstance(signature, bytes)
    
    def test_signature_has_expected_length(self):
        _, secret_key = generate_dilithium_keypair()
        message = b"test message"
        signature = dilithium_sign(message, secret_key)
        assert len(signature) >= 2000
    
    def test_verify_valid_signature(self):
        public_key, secret_key = generate_dilithium_keypair()
        message = b"test message"
        signature = dilithium_sign(message, secret_key)
        assert dilithium_verify(message, signature, public_key) is True
    
    def test_simulated_sign_verify_consistency(self):
        sim = SimulatedDilithium()
        public_key, secret_key = sim.generate_keypair()
        message = b"test message for signing"
        signature = sim.sign(message, secret_key)
        assert sim.verify(message, signature, public_key) is True


class TestPQCEncryptDecrypt:
    
    def test_pqc_encrypt_returns_tuple(self):
        plaintext = b"test plaintext"
        result = pqc_encrypt(plaintext)
        assert isinstance(result, tuple)
        assert len(result) == 3
    
    def test_pqc_encrypt_returns_plaintext_unchanged(self):
        plaintext = b"test plaintext"
        returned_plaintext, _, _ = pqc_encrypt(plaintext)
        assert returned_plaintext == plaintext
    
    def test_pqc_encrypt_returns_encapsulated_key(self):
        plaintext = b"test plaintext"
        _, encapsulated_key, _ = pqc_encrypt(plaintext)
        assert isinstance(encapsulated_key, bytes)
        assert len(encapsulated_key) >= 1000
    
    def test_pqc_encrypt_returns_shared_secret(self):
        plaintext = b"test plaintext"
        _, _, shared_secret = pqc_encrypt(plaintext)
        assert isinstance(shared_secret, bytes)
        assert len(shared_secret) == 32


class TestPQCInfo:
    
    def test_is_pqc_available_returns_bool(self):
        result = is_pqc_available()
        assert isinstance(result, bool)
    
    def test_get_pqc_info_returns_dict(self):
        result = get_pqc_info()
        assert isinstance(result, dict)
    
    def test_get_pqc_info_contains_required_keys(self):
        result = get_pqc_info()
        assert "available" in result
        assert "kem_algorithm" in result
        assert "signature_algorithm" in result
        assert "mode" in result
    
    def test_get_pqc_info_mode_matches_availability(self):
        result = get_pqc_info()
        if result["available"]:
            assert result["mode"] == "native"
        else:
            assert result["mode"] == "simulated"
            assert result["warning"] is not None
