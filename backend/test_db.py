import asyncio
import aiosqlite

async def test_db():
    print("Connecting...")
    async with aiosqlite.connect("data/qumail.db") as db:
        print("Connected.")
        
        # Test query
        cursor = await db.execute("SELECT count(*) FROM accounts")
        res = await cursor.fetchone()
        print("Accounts:", res[0])

asyncio.run(test_db())
