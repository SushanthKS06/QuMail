import sys
import os
import time

# Add backend to path
sys.path.append(os.path.dirname(__file__))

# Set dev mode
os.environ["QUMAIL_DEV_MODE"] = "1"

from tests.test_quantum_entropy import TestQuantumSimEntropy, TestSecureRandomIntegration

def run_tests():
    print("Running TestQuantumSimEntropy...")
    t = TestQuantumSimEntropy()
    
    print(" - test_entropy_pool_initialization")
    t.test_entropy_pool_initialization()
    
    print(" - test_entropy_extraction")
    t.test_entropy_extraction()
    
    print(" - test_entropy_health_check")
    t.test_entropy_health_check()
    
    print(" - test_entropy_byte_distribution")
    try:
        t.test_entropy_byte_distribution()
        print("   PASS")
    except AssertionError as e:
        print(f"   FAIL: {e}")
    except Exception as e:
        print(f"   ERROR: {e}")

    print("\nRunning TestSecureRandomIntegration...")
    t2 = TestSecureRandomIntegration()
    
    print(" - test_secure_random_uses_quantum_sim")
    try:
        t2.test_secure_random_uses_quantum_sim()
        print("   PASS")
    except AssertionError as e:
        print(f"   FAIL: {e}")
    except Exception as e:
        print(f"   ERROR: {e}")

if __name__ == "__main__":
    run_tests()
