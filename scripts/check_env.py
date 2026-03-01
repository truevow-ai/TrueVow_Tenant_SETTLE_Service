"""
Check Environment Variables

Quick script to verify which .env file is being loaded and what variables are set.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Check which .env files exist
project_root = Path(__file__).parent.parent
env_local = project_root / '.env.local'
env_file = project_root / '.env'

print("\n" + "="*70)
print("🔍 SETTLE Service - Environment Variable Checker")
print("="*70)

print(f"\n📁 Project root: {project_root}")
print(f"\n📄 Checking for .env files...")
print(f"   .env.local exists: {'✅ YES' if env_local.exists() else '❌ NO'}")
print(f"   .env exists:       {'✅ YES' if env_file.exists() else '❌ NO'}")

# Load environment variables
if env_local.exists():
    load_dotenv(env_local)
    print(f"\n✅ Loaded from: .env.local")
elif env_file.exists():
    load_dotenv(env_file)
    print(f"\n✅ Loaded from: .env")
else:
    load_dotenv()
    print(f"\n⚠️  No .env file found, using system environment only")

# Check for SETTLE-specific variables (Provider-Agnostic)
print("\n" + "="*70)
print("🔑 SETTLE-Prefixed Variables (Provider-Agnostic - RECOMMENDED):")
print("="*70)

settle_vars = {
    'SETTLE_DATABASE_URL': os.environ.get('SETTLE_DATABASE_URL'),
    'SETTLE_DATABASE_ANON_KEY': os.environ.get('SETTLE_DATABASE_ANON_KEY'),
    'SETTLE_DATABASE_SERVICE_KEY': os.environ.get('SETTLE_DATABASE_SERVICE_KEY'),
    'SETTLE_SECRET_KEY': os.environ.get('SETTLE_SECRET_KEY'),
    'SETTLE_API_KEY_SALT': os.environ.get('SETTLE_API_KEY_SALT'),
    'SETTLE_USE_MOCK_DATA': os.environ.get('SETTLE_USE_MOCK_DATA'),
    'SETTLE_DEBUG': os.environ.get('SETTLE_DEBUG'),
    'SETTLE_PORT': os.environ.get('SETTLE_PORT'),
}

for var_name, var_value in settle_vars.items():
    if var_value:
        # Show first 20 chars for security
        display_value = var_value[:20] + '...' if len(var_value) > 20 else var_value
        print(f"✅ {var_name:<35} = {display_value}")
    else:
        print(f"❌ {var_name:<35} = NOT SET")

# Check for SETTLE-specific Supabase variables
print("\n" + "="*70)
print("🔑 SETTLE-Prefixed Variables (Provider-Specific - Supabase):")
print("="*70)

settle_supabase_vars = {
    'SETTLE_SUPABASE_URL': os.environ.get('SETTLE_SUPABASE_URL'),
    'SETTLE_SUPABASE_ANON_KEY': os.environ.get('SETTLE_SUPABASE_ANON_KEY'),
    'SETTLE_SUPABASE_SERVICE_KEY': os.environ.get('SETTLE_SUPABASE_SERVICE_KEY'),
}

for var_name, var_value in settle_supabase_vars.items():
    if var_value:
        display_value = var_value[:20] + '...' if len(var_value) > 20 else var_value
        print(f"✅ {var_name:<35} = {display_value}")
    else:
        print(f"❌ {var_name:<35} = NOT SET")

# Check for unprefixed variables (fallback)
print("\n" + "="*70)
print("🔑 Unprefixed Variables (Backwards Compatibility):")
print("="*70)

unprefixed_vars = {
    'DATABASE_URL': os.environ.get('DATABASE_URL'),
    'DATABASE_ANON_KEY': os.environ.get('DATABASE_ANON_KEY'),
    'DATABASE_SERVICE_KEY': os.environ.get('DATABASE_SERVICE_KEY'),
    'SUPABASE_URL': os.environ.get('SUPABASE_URL'),
    'SUPABASE_KEY': os.environ.get('SUPABASE_KEY'),
    'SUPABASE_SERVICE_KEY': os.environ.get('SUPABASE_SERVICE_KEY'),
    'SECRET_KEY': os.environ.get('SECRET_KEY'),
    'API_KEY_SALT': os.environ.get('API_KEY_SALT'),
}

for var_name, var_value in unprefixed_vars.items():
    if var_value:
        display_value = var_value[:20] + '...' if len(var_value) > 20 else var_value
        print(f"✅ {var_name:<35} = {display_value}")
    else:
        print(f"❌ {var_name:<35} = NOT SET")

# Summary
print("\n" + "="*70)
print("📊 Summary:")
print("="*70)

# Check for database credentials (any naming convention)
has_database_provider_agnostic = all([
    os.environ.get('SETTLE_DATABASE_URL'),
    os.environ.get('SETTLE_DATABASE_ANON_KEY')
])

has_database_supabase = all([
    os.environ.get('SETTLE_SUPABASE_URL'),
    os.environ.get('SETTLE_SUPABASE_ANON_KEY')
])

has_database_unprefixed_generic = all([
    os.environ.get('DATABASE_URL'),
    os.environ.get('DATABASE_ANON_KEY')
])

has_database_unprefixed_supabase = all([
    os.environ.get('SUPABASE_URL'),
    os.environ.get('SUPABASE_KEY')
])

has_database = (
    has_database_provider_agnostic or 
    has_database_supabase or 
    has_database_unprefixed_generic or
    has_database_unprefixed_supabase
)

if has_database_provider_agnostic:
    print("✅ All required SETTLE-prefixed (provider-agnostic) variables are set")
    print("   Using: SETTLE_DATABASE_URL, SETTLE_DATABASE_ANON_KEY")
    print("   ⭐ RECOMMENDED naming convention!")
elif has_database_supabase:
    print("✅ All required SETTLE-prefixed (Supabase-specific) variables are set")
    print("   Using: SETTLE_SUPABASE_URL, SETTLE_SUPABASE_ANON_KEY")
elif has_database_unprefixed_generic:
    print("✅ All required unprefixed (provider-agnostic) variables are set")
    print("   Using: DATABASE_URL, DATABASE_ANON_KEY")
elif has_database_unprefixed_supabase:
    print("✅ All required unprefixed (Supabase-specific) variables are set")
    print("   Using: SUPABASE_URL, SUPABASE_KEY")

if has_database:
    print("\n   ✅ You're ready to run the SETTLE service!")
else:
    print("❌ Missing required database credentials")
    print("\n   You need database credentials in ONE of these formats:")
    print("\n   1. RECOMMENDED (provider-agnostic, prefixed):")
    print("      SETTLE_DATABASE_URL + SETTLE_DATABASE_ANON_KEY")
    print("\n   2. Provider-specific, prefixed:")
    print("      SETTLE_SUPABASE_URL + SETTLE_SUPABASE_ANON_KEY")
    print("\n   3. Provider-agnostic, unprefixed:")
    print("      DATABASE_URL + DATABASE_ANON_KEY")
    print("\n   4. Provider-specific, unprefixed:")
    print("      SUPABASE_URL + SUPABASE_KEY")
    print("\n   Also recommended:")
    print("   - SETTLE_DATABASE_SERVICE_KEY (or SERVICE_KEY for your provider)")
    print("   - SETTLE_SECRET_KEY")
    print("   - SETTLE_API_KEY_SALT")

print("\n" + "="*70)
print()

