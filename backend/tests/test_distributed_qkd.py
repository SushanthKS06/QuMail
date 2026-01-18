import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import sys
import base64
from datetime import datetime, timezone

# Add backend and key_manager to path
# Add backend and key_manager to path
backend_path = Path(__file__).parent.parent
key_manager_path = Path(__file__).parent.parent.parent / "key_manager"

# Insert key_manager FIRST so 'config' resolves to key_manager/config.py
sys.path.insert(0, str(key_manager_path))

# Import settings NOW while key_manager is the only 'config' provider
from config import settings

# NOW add backend for crypto_engine dependencies
sys.path.insert(1, str(backend_path))

from core.key_pool import KeyPool, KeyEntry
from core.qkd_link import QKDLink

class TestDistributedQKD(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # Reset settings
        settings.peers = {}
        settings.local_peer_id = "km-local"
        
    async def asyncSetUp(self):
        self.pool = KeyPool()
        self.pool.initialize(otp_bytes=1000, aes_keys=10)
        
    async def asyncTearDown(self):
        self.pool.shutdown()

    @patch("httpx.AsyncClient")
    async def test_qkd_link_push_key(self, mock_client_cls):
        # Setup
        mock_instance = AsyncMock()
        mock_client_cls.return_value = mock_instance
        mock_instance.post.return_value.status_code = 200
        
        settings.peers = {"remote-peer": "http://remote:8100"}
        settings.qkd_link_secret = "secret123"
        
        link = QKDLink()
        # Hack to inject mock since QKDLink init creates client
        link._http_client = mock_instance
        
        entry = KeyEntry(
            key_id="test-key-1",
            key_material=b"\x00" * 32,
            peer_id="remote-peer",
            key_type="aes_seed",
            created_at=datetime.now(timezone.utc),
            user_id="user1"
        )
        
        # Execute
        await link.push_key("remote-peer", entry)
        
        # Wait for background tasks to complete
        if link._background_tasks:
            await asyncio.gather(*link._background_tasks)
        
        # Verify
        mock_instance.post.assert_called_once()
        call_args = mock_instance.post.call_args
        url = call_args[0][0]
        kwargs = call_args[1]
        
        self.assertEqual(url, "http://remote:8100/api/v1/keys/exchange")
        self.assertEqual(kwargs["headers"]["X-QKD-Link-Secret"], "secret123")
        
        payload = kwargs["json"]
        self.assertEqual(payload["key_id"], "test-key-1")
        self.assertEqual(payload["peer_id"], "km-local")
        
        await link.shutdown()

    async def test_key_pool_hook_integration(self):
        hook_mock = MagicMock()
        self.pool.register_allocation_hook(hook_mock)
        
        # Execute
        self.pool.allocate_key(peer_id="remote-peer", size=32)
        
        # Verify
        hook_mock.assert_called_once()
        args = hook_mock.call_args[0]
        self.assertEqual(args[0], "remote-peer")
        self.assertIsInstance(args[1], KeyEntry)

    async def test_key_injection(self):
        entry = KeyEntry(
            key_id="injected-key-1",
            key_material=b"\x99" * 32,
            peer_id="remote-sender",
            key_type="aes_seed",
            created_at=datetime.now(timezone.utc),
            user_id="user2"
        )
        
        # Inject
        self.pool.inject_key(entry)
        
        # Verify
        retrieved = self.pool.get_key("injected-key-1")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.key_material, b"\x99" * 32)
        self.assertEqual(retrieved.peer_id, "remote-sender")

if __name__ == "__main__":
    import traceback
    try:
        unittest.main(verbosity=2)
    except Exception:
        traceback.print_exc()
