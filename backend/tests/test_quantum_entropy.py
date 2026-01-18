import pytest
import os
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))


class TestQuantumSimEntropy:

    def test_entropy_pool_initialization(self):
        from crypto_engine.quantum_sim import EntropyPool
        
        pool = EntropyPool()
        stats = pool.get_stats()
        
        assert len(stats["sources_available"]) >= 2
        assert "os_urandom" in stats["sources_available"]
    
    def test_entropy_extraction(self):
        from crypto_engine.quantum_sim import EntropyPool
        
        pool = EntropyPool()
        data = pool.extract(64)
        
        assert len(data) == 64
        assert isinstance(data, bytes)
    
    def test_entropy_uniqueness(self):
        from crypto_engine.quantum_sim import EntropyPool
        
        pool = EntropyPool()
        samples = [pool.extract(32) for _ in range(100)]
        
        unique_samples = set(samples)
        assert len(unique_samples) == 100
    
    def test_entropy_health_check(self):
        from crypto_engine.quantum_sim import EntropyPool
        
        pool = EntropyPool()
        result = pool.health_check()
        
        assert isinstance(result, bool)
        assert result is True
    
    def test_chacha20_csprng_generation(self):
        from crypto_engine.quantum_sim import ChaCha20CSPRNG, EntropyPool
        
        pool = EntropyPool()
        csprng = ChaCha20CSPRNG(pool)
        
        data = csprng.generate(128)
        
        assert len(data) == 128
        assert isinstance(data, bytes)
    
    def test_csprng_uniqueness(self):
        from crypto_engine.quantum_sim import ChaCha20CSPRNG, EntropyPool
        
        pool = EntropyPool()
        csprng = ChaCha20CSPRNG(pool)
        
        samples = [csprng.generate(32) for _ in range(100)]
        unique_samples = set(samples)
        
        assert len(unique_samples) == 100
    
    def test_global_generate_quantum_bytes(self):
        from crypto_engine.quantum_sim import generate_quantum_bytes
        
        data = generate_quantum_bytes(256)
        
        assert len(data) == 256
        assert isinstance(data, bytes)
    
    def test_generate_quantum_key(self):
        from crypto_engine.quantum_sim import generate_quantum_key
        
        key_material, key_id = generate_quantum_key(32)
        
        assert len(key_material) == 32
        assert len(key_id) == 32
    
    def test_entropy_stats(self):
        from crypto_engine.quantum_sim import get_entropy_stats
        
        stats = get_entropy_stats()
        
        assert "entropy_pool" in stats
        assert "csprng" in stats
        assert "sources_available" in stats["entropy_pool"]
    
    def test_force_reseed(self):
        from crypto_engine.quantum_sim import force_reseed, get_entropy_stats
        
        initial_stats = get_entropy_stats()
        
        force_reseed()
        
        new_stats = get_entropy_stats()
        assert new_stats["entropy_pool"]["reseed_count"] > initial_stats["entropy_pool"]["reseed_count"]
    
    def test_entropy_byte_distribution(self):
        from crypto_engine.quantum_sim import generate_quantum_bytes
        
        data = generate_quantum_bytes(10000)
        
        byte_counts = [0] * 256
        for b in data:
            byte_counts[b] += 1
        
        expected = len(data) / 256
        chi_squared = sum((count - expected) ** 2 / expected for count in byte_counts)
        
        assert chi_squared < 350
    
    def test_large_key_generation(self):
        from crypto_engine.quantum_sim import generate_quantum_bytes
        
        data = generate_quantum_bytes(1024 * 1024)
        
        assert len(data) == 1024 * 1024


class TestSecureRandomIntegration:

    def test_secure_random_uses_quantum_sim(self):
        from crypto_engine.secure_random import secure_random_bytes, _use_quantum_sim
        
        data = secure_random_bytes(32)
        
        assert len(data) == 32
        assert _use_quantum_sim is True
    
    def test_generate_encryption_key(self):
        from crypto_engine.secure_random import generate_encryption_key
        
        key, key_id = generate_encryption_key(32)
        
        assert len(key) == 32
        assert len(key_id) > 0
    
    def test_get_random_stats(self):
        from crypto_engine.secure_random import get_random_stats
        
        stats = get_random_stats()
        
        assert "entropy_pool" in stats or "source" in stats
    
    def test_check_entropy_health(self):
        from crypto_engine.secure_random import check_entropy_health
        
        result = check_entropy_health()
        
        assert result is True


class TestKeyPoolPersistence:

    @pytest.fixture
    def temp_persistence_path(self, tmp_path):
        return tmp_path / "test_keystore.enc"
    
    @pytest.fixture
    def temp_audit_path(self, tmp_path):
        return tmp_path / "test_audit.log"
    
    def test_key_pool_with_persistence(self, temp_persistence_path, temp_audit_path):
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "key_manager"))
        
        from core.key_pool import KeyPool
        
        pool = KeyPool(
            persistence_enabled=True,
            persistence_path=temp_persistence_path,
            persistence_password="test_password_123",
            audit_path=temp_audit_path,
        )
        pool.initialize(otp_bytes=1000, aes_keys=10)
        
        entry = pool.allocate_key(
            peer_id="test@example.com",
            size=32,
            key_type="aes_seed",
            user_id="user1",
        )
        
        assert entry.key_id is not None
        assert len(entry.key_material) == 32
        assert entry.user_id == "user1"
        
        assert temp_persistence_path.exists()
        
        pool.shutdown()
    
    def test_key_pool_restore_after_restart(self, temp_persistence_path, temp_audit_path):
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "key_manager"))
        
        from core.key_pool import KeyPool
        
        pool1 = KeyPool(
            persistence_enabled=True,
            persistence_path=temp_persistence_path,
            persistence_password="test_password_123",
        )
        pool1.initialize(otp_bytes=1000, aes_keys=10)
        
        entry = pool1.allocate_key(
            peer_id="test@example.com",
            size=32,
            key_type="aes_seed",
        )
        key_id = entry.key_id
        original_material = entry.key_material
        
        pool1.shutdown()
        
        pool2 = KeyPool(
            persistence_enabled=True,
            persistence_path=temp_persistence_path,
            persistence_password="test_password_123",
        )
        pool2.initialize(otp_bytes=1000, aes_keys=10)
        
        restored_entry = pool2.get_key(key_id)
        
        assert restored_entry is not None
        assert restored_entry.key_material == original_material
        
        pool2.shutdown()
    
    def test_audit_logging(self, temp_persistence_path, temp_audit_path):
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "key_manager"))
        
        from core.key_pool import KeyPool
        
        pool = KeyPool(
            persistence_enabled=True,
            persistence_path=temp_persistence_path,
            persistence_password="test_password_123",
            audit_path=temp_audit_path,
        )
        pool.initialize(otp_bytes=1000, aes_keys=10)
        
        entry = pool.allocate_key(
            peer_id="test@example.com",
            size=32,
            key_type="aes_seed",
        )
        
        pool.consume_key(entry.key_id)
        
        assert temp_audit_path.exists()
        
        audit_content = temp_audit_path.read_text()
        assert "ALLOCATE" in audit_content
        assert "CONSUME" in audit_content
        
        pool.shutdown()


class TestAuditLogIntegrity:

    def test_hash_chain_verification(self, tmp_path):
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "key_manager"))
        
        from core.persistent_store import AuditLogger
        
        audit_path = tmp_path / "audit.log"
        logger = AuditLogger(audit_path)
        
        logger.log("ACTION_1", "key-001", {"detail": "test1"})
        logger.log("ACTION_2", "key-002", {"detail": "test2"})
        logger.log("ACTION_3", "key-003", {"detail": "test3"})
        
        assert logger.verify_chain() is True
    
    def test_tamper_detection(self, tmp_path):
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "key_manager"))
        
        from core.persistent_store import AuditLogger
        
        audit_path = tmp_path / "audit.log"
        logger = AuditLogger(audit_path)
        
        logger.log("ACTION_1", "key-001", {"detail": "test1"})
        logger.log("ACTION_2", "key-002", {"detail": "test2"})
        
        content = audit_path.read_text()
        tampered = content.replace("key-001", "key-XXX")
        audit_path.write_text(tampered)
        
        new_logger = AuditLogger(audit_path)
        assert new_logger.verify_chain() is False
