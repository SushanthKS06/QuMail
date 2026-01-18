import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))


class TestKeyManagerAPI:

    @pytest.fixture
    def mock_key_pool(self):
        from key_manager.core.key_pool import KeyPool
        pool = KeyPool()
        pool.initialize(otp_bytes=10000, aes_keys=100)
        return pool

    def test_key_pool_initialization(self, mock_key_pool):
        stats = mock_key_pool.get_stats()
        assert stats["otp_available"] == 10000
        assert stats["aes_available"] == 100
        assert stats["total_allocated"] == 0

    def test_allocate_aes_key(self, mock_key_pool):
        entry = mock_key_pool.allocate_key(
            peer_id="test@example.com",
            size=32,
            key_type="aes_seed",
        )
        assert entry.key_id is not None
        assert len(entry.key_material) == 32
        assert entry.peer_id == "test@example.com"
        assert entry.key_type == "aes_seed"
        assert entry.consumed is False

    def test_allocate_otp_key(self, mock_key_pool):
        entry = mock_key_pool.allocate_key(
            peer_id="test@example.com",
            size=100,
            key_type="otp",
        )
        assert entry.key_id is not None
        assert len(entry.key_material) == 100
        assert entry.key_type == "otp"
        
        stats = mock_key_pool.get_stats()
        assert stats["otp_available"] == 10000 - 100

    def test_otp_exhaustion(self, mock_key_pool):
        with pytest.raises(ValueError, match="Insufficient OTP"):
            mock_key_pool.allocate_key(
                peer_id="test@example.com",
                size=20000,
                key_type="otp",
            )

    def test_get_key_by_id(self, mock_key_pool):
        entry = mock_key_pool.allocate_key(
            peer_id="test@example.com",
            size=32,
            key_type="aes_seed",
        )
        
        retrieved = mock_key_pool.get_key(entry.key_id)
        assert retrieved is not None
        assert retrieved.key_id == entry.key_id

    def test_get_nonexistent_key(self, mock_key_pool):
        retrieved = mock_key_pool.get_key("nonexistent-key-id")
        assert retrieved is None

    def test_consume_key(self, mock_key_pool):
        entry = mock_key_pool.allocate_key(
            peer_id="test@example.com",
            size=32,
            key_type="aes_seed",
        )
        
        success = mock_key_pool.consume_key(entry.key_id)
        assert success is True
        
        retrieved = mock_key_pool.get_key(entry.key_id)
        assert retrieved.consumed is True

    def test_consume_already_consumed_key(self, mock_key_pool):
        entry = mock_key_pool.allocate_key(
            peer_id="test@example.com",
            size=32,
            key_type="aes_seed",
        )
        
        mock_key_pool.consume_key(entry.key_id)
        success = mock_key_pool.consume_key(entry.key_id)
        assert success is False

    def test_delete_key(self, mock_key_pool):
        entry = mock_key_pool.allocate_key(
            peer_id="test@example.com",
            size=32,
            key_type="aes_seed",
        )
        
        success = mock_key_pool.delete_key(entry.key_id)
        assert success is True
        
        retrieved = mock_key_pool.get_key(entry.key_id)
        assert retrieved is None

    def test_add_otp_material(self, mock_key_pool):
        initial_stats = mock_key_pool.get_stats()
        initial_otp = initial_stats["otp_available"]
        
        mock_key_pool.add_otp_material(5000)
        
        new_stats = mock_key_pool.get_stats()
        assert new_stats["otp_available"] == initial_otp + 5000

    def test_add_aes_keys(self, mock_key_pool):
        initial_stats = mock_key_pool.get_stats()
        initial_aes = initial_stats["aes_available"]
        
        mock_key_pool.add_aes_keys(50)
        
        new_stats = mock_key_pool.get_stats()
        assert new_stats["aes_available"] == initial_aes + 50

    def test_key_has_expiration(self, mock_key_pool):
        entry = mock_key_pool.allocate_key(
            peer_id="test@example.com",
            size=32,
            key_type="aes_seed",
        )
        assert entry.expires_at is not None
        assert entry.expires_at > entry.created_at


class TestKeyLifecycle:

    def test_key_lifecycle_states(self):
        from key_store.lifecycle import KeyLifecycle, KeyState
        
        lifecycle = KeyLifecycle()
        key_id = "test-key-123"
        
        lifecycle.track(key_id, "aes_seed")
        assert lifecycle.get_state(key_id) == KeyState.PROVISIONED
        
        lifecycle.reserve(key_id)
        assert lifecycle.get_state(key_id) == KeyState.RESERVED
        
        lifecycle.mark_used(key_id)
        assert lifecycle.get_state(key_id) == KeyState.USED
        
        lifecycle.mark_consumed(key_id)
        assert lifecycle.get_state(key_id) == KeyState.CONSUMED
        
        lifecycle.mark_zeroized(key_id)
        assert lifecycle.get_state(key_id) == KeyState.ZEROIZED

    def test_cannot_reserve_consumed_key(self):
        from key_store.lifecycle import KeyLifecycle, KeyState
        
        lifecycle = KeyLifecycle()
        key_id = "test-key-123"
        
        lifecycle.track(key_id, "aes_seed")
        lifecycle.mark_consumed(key_id)
        
        success = lifecycle.reserve(key_id)
        assert success is False

    def test_is_consumable(self):
        from key_store.lifecycle import KeyLifecycle
        
        lifecycle = KeyLifecycle()
        key_id = "test-key-123"
        
        lifecycle.track(key_id, "aes_seed")
        assert lifecycle.is_consumable(key_id) is True
        
        lifecycle.mark_consumed(key_id)
        assert lifecycle.is_consumable(key_id) is False

    def test_lifecycle_stats(self):
        from key_store.lifecycle import KeyLifecycle
        
        lifecycle = KeyLifecycle()
        
        lifecycle.track("key1", "aes")
        lifecycle.track("key2", "aes")
        lifecycle.track("key3", "otp")
        
        lifecycle.mark_consumed("key1")
        
        stats = lifecycle.get_stats()
        assert stats["provisioned"] == 2
        assert stats["consumed"] == 1
