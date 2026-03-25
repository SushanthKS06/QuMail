
import sys
import unittest
import ctypes
import gc
from pathlib import Path

# Add project roots to path
backend_path = Path(__file__).parent.parent
key_manager_path = Path(__file__).parent.parent.parent / "key_manager"
sys.path.insert(0, str(key_manager_path))

from core.key_pool import KeyPool, KeyEntry
from datetime import datetime, timezone

class TestMemoryZeroization(unittest.TestCase):
    
    def test_zeroization_clears_memory(self):
        """
        Verify that _zeroize_key actually overwrites the memory address
        where the key material was stored.
        """
        pool = KeyPool()
        
        # 1. Create a sensitive key (bytearray)
        original_pattern = b"\xAA" * 32
        key_material = bytearray(original_pattern)
        
        # 2. Get the memory address of the buffer
        # We need the address of the actual data, not the python object
        addr, length = key_material.buffer_info() if hasattr(key_material, "buffer_info") else (id(key_material), len(key_material))
        
        # For bytearray, we can use ctypes to peek at memory
        # Note: id(bytearray) gives address of the object struct, not the data buffer usually.
        # However, for a quick check, we can rely on the fact that if we zeroize IN PLACE,
        # the content should change.
        
        entry = KeyEntry(
            key_id="test-zero",
            key_material=key_material,
            peer_id="test",
            key_type="aes",
            created_at=datetime.now(timezone.utc)
        )
        
        # 3. Verify content before zeroization
        self.assertEqual(entry.key_material, original_pattern)
        
        # 4. Zeroize
        pool._zeroize_key(entry)
        
        # 5. Verify content - should be empty/cleared
        # Because our implementation now does:
        #   entry.key_material = bytearray()
        # The object reference in 'entry' now points to a NEW empty bytearray.
        self.assertEqual(len(entry.key_material), 0)
        
        # BUT, the critical security question is: Did the OLD memory get wiped?
        # Since we held a reference to 'key_material' in this test function...
        
        # Let's check the local variable 'key_material'
        # If the zeroization function modified the object in-place (iterating and setting to 0),
        # then our local reference should ALSO be zeroed.
        
        zeroed_pattern = b"\x00" * 32
        self.assertEqual(key_material, zeroed_pattern, 
            "CRITICAL FAIL: The original memory buffer was not overwritten! Zeroization is superficial.")
            
        print("SUCCESS: Original memory buffer was securely overwritten.")

if __name__ == "__main__":
    unittest.main()
