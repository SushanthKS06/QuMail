import asyncio
import aiosqlite
from storage.database import get_stored_accounts, init_database

async def test_lock():
    print("Init db...")
    await init_database()
    print("Init done.")
    
    print("Get accounts...")
    accs = await get_stored_accounts()
    print("Accounts:", len(accs))

asyncio.run(test_lock())
