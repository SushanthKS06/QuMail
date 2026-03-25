import asyncio
import sys
import logging

logging.basicConfig(level=logging.DEBUG)

# Add backend to path so we can import
sys.path.append('.')

from qkd_client import get_key_status

async def test_qkd():
    print("Fetching key status...")
    status = await get_key_status()
    print("Status:", status)

asyncio.run(test_qkd())
