import traceback
import sys

sys.stderr = sys.stdout

try:
    print("Starting import test...")
    print("1. Testing config import...")
    from config import settings
    print("   Config OK")
    
    print("2. Testing core.key_pool import...")
    from core.key_pool import KeyPool
    print("   KeyPool OK")
    
    print("3. Testing api imports...")
    from api import keys, status
    print("   API OK")
    
    print("4. Testing core.qkd_link import...")
    from core.qkd_link import get_qkd_link
    print("   QKD Link OK")
    
    print("All imports successful!")
    
except Exception as e:
    print(f"\nError: {e}")
    traceback.print_exc()
