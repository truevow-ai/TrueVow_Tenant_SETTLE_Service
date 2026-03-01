"""Test database connection"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv
import pathlib

async def test():
    # Load .env.local from project root
    project_root = pathlib.Path(__file__).parent.parent.parent
    env_local = project_root / '.env.local'
    if env_local.exists():
        load_dotenv(env_local)
    
    database_url = os.getenv("SETTLE_DATABASE_URL")
    print(f"Connection string: {database_url[:60]}..." if database_url else "NOT FOUND")
    
    if not database_url:
        print("ERROR: SETTLE_DATABASE_URL not found")
        return
    
    # Try direct connection (5432)
    print("\nTrying direct connection (port 5432)...")
    try:
        conn = await asyncpg.connect(database_url)
        print("SUCCESS: Connected!")
        await conn.close()
    except Exception as e:
        print(f"FAILED: {e}")
        
        # Try connection pooler (6543)
        if ":5432" in database_url:
            pooler_url = database_url.replace(":5432", ":6543")
            print(f"\nTrying connection pooler (port 6543)...")
            print(f"URL: {pooler_url[:60]}...")
            try:
                conn = await asyncpg.connect(pooler_url)
                print("SUCCESS: Connected via pooler!")
                await conn.close()
                print(f"\nUse this connection string: {pooler_url}")
            except Exception as e2:
                print(f"FAILED: {e2}")

if __name__ == "__main__":
    asyncio.run(test())

