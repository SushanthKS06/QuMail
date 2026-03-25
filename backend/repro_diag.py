import sys
import os
import asyncio

# Add backend to path
sys.path.append(os.path.dirname(__file__))

from api.diagnostics import _test_aes_encryption, _test_otp_encryption, _test_pqc_encryption

async def main():
    print("Running AES Test...")
    res = await _test_aes_encryption()
    print(f"AES: {res.success} - {res.message}")
    if not res.success:
        print(f"Error: {res.message}")

    print("\nRunning OTP Test...")
    res = await _test_otp_encryption()
    print(f"OTP: {res.success} - {res.message}")

    print("\nRunning PQC Test...")
    res = await _test_pqc_encryption()
    print(f"PQC: {res.success} - {res.message}")

if __name__ == "__main__":
    asyncio.run(main())
