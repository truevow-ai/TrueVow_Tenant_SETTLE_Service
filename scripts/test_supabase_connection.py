"""
Test Supabase Connection for SETTLE Service

Verifies that:
1. Supabase connection works
2. All settle_ tables exist
3. Can read/write data
"""

import os
import sys
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables (check .env.local first, then .env)
from pathlib import Path
env_local = Path(__file__).parent.parent / '.env.local'
env_file = Path(__file__).parent.parent / '.env'

if env_local.exists():
    load_dotenv(env_local)
    print(f"📁 Loaded environment from: .env.local")
elif env_file.exists():
    load_dotenv(env_file)
    print(f"📁 Loaded environment from: .env")
else:
    load_dotenv()  # Try default locations
    print(f"📁 Loaded environment from default locations")

def test_supabase_connection():
    """Test Supabase connection and table existence"""
    
    try:
        from supabase import create_client, Client
    except ImportError:
        print("❌ Supabase client not installed")
        print("   Run: pip install supabase")
        return False
    
    # Get credentials (supports multiple naming conventions)
    # Priority: SETTLE_DATABASE_* > SETTLE_SUPABASE_* > DATABASE_* > SUPABASE_*
    url = (
        os.environ.get("SETTLE_DATABASE_URL") or 
        os.environ.get("SETTLE_SUPABASE_URL") or
        os.environ.get("DATABASE_URL") or
        os.environ.get("SUPABASE_URL")
    )
    key = (
        os.environ.get("SETTLE_DATABASE_ANON_KEY") or
        os.environ.get("SETTLE_SUPABASE_ANON_KEY") or
        os.environ.get("DATABASE_ANON_KEY") or
        os.environ.get("SUPABASE_KEY")
    )
    
    if not url or not key:
        print("❌ Missing database credentials in .env.local file")
        print("")
        print("   Required (provider-agnostic, prefixed - RECOMMENDED):")
        print("     SETTLE_DATABASE_URL, SETTLE_DATABASE_ANON_KEY")
        print("")
        print("   Or (provider-specific, prefixed):")
        print("     SETTLE_SUPABASE_URL, SETTLE_SUPABASE_ANON_KEY")
        print("")
        print("   Or (unprefixed):")
        print("     DATABASE_URL, DATABASE_ANON_KEY")
        print("     SUPABASE_URL, SUPABASE_KEY")
        return False
    
    print("\n" + "="*60)
    print("🧪 SETTLE Service - Supabase Connection Test")
    print("="*60)
    
    # Create client
    try:
        supabase: Client = create_client(url, key)
        print(f"✅ Supabase client created")
        print(f"   URL: {url}")
    except Exception as e:
        print(f"❌ Failed to create Supabase client: {str(e)}")
        return False
    
    # Test each table
    tables = [
        'settle_contributions',
        'settle_api_keys',
        'settle_founding_members',
        'settle_queries',
        'settle_reports',
        'settle_waitlist'
    ]
    
    print(f"\n📊 Testing tables...")
    print("-" * 60)
    
    all_tables_exist = True
    
    for table in tables:
        try:
            response = supabase.table(table).select("count", count='exact').execute()
            count = response.count
            print(f"✅ {table:<30} {count:>5} rows")
        except Exception as e:
            print(f"❌ {table:<30} ERROR: {str(e)}")
            all_tables_exist = False
    
    # Test views
    print(f"\n📊 Testing views...")
    print("-" * 60)
    
    try:
        response = supabase.table('settle_founding_member_stats').select("*").execute()
        print(f"✅ settle_founding_member_stats    Available")
    except Exception as e:
        print(f"❌ settle_founding_member_stats    ERROR: {str(e)}")
        all_tables_exist = False
    
    # Test write (insert and delete)
    print(f"\n✍️  Testing write permissions...")
    print("-" * 60)
    
    try:
        # Insert test record
        test_data = {
            "email": "test@example.com",
            "law_firm_name": "Test Firm",
            "state": "AZ",
            "status": "pending"
        }
        
        response = supabase.table('settle_waitlist').insert(test_data).execute()
        
        if response.data and len(response.data) > 0:
            test_id = response.data[0]['id']
            print(f"✅ Insert successful (ID: {test_id})")
            
            # Delete test record
            supabase.table('settle_waitlist').delete().eq('id', test_id).execute()
            print(f"✅ Delete successful")
        else:
            print(f"⚠️  Insert returned no data")
            
    except Exception as e:
        print(f"❌ Write test failed: {str(e)}")
        all_tables_exist = False
    
    # Summary
    print("\n" + "="*60)
    if all_tables_exist:
        print("✅ ALL TESTS PASSED")
        print("="*60)
        print("\n📝 Next Steps:")
        print("   1. Start SETTLE service: uvicorn app.main:app --reload")
        print("   2. Test API: http://localhost:8002/docs")
        print("   3. Seed test data: python scripts/seed_test_data.py")
        print()
        return True
    else:
        print("❌ SOME TESTS FAILED")
        print("="*60)
        print("\n📝 Troubleshooting:")
        print("   1. Verify Supabase project is active")
        print("   2. Run schema: database/schemas/settle_supabase.sql")
        print("   3. Check credentials in .env file")
        print("   4. See: database/SUPABASE_SETUP_GUIDE.md")
        print()
        return False


if __name__ == "__main__":
    success = test_supabase_connection()
    sys.exit(0 if success else 1)

