"""
Generate secure keys for .env.local file

This script generates cryptographically secure random keys for:
- SECRET_KEY
- API_KEY_SALT

Usage:
    python scripts/generate_env_keys.py
"""

import secrets


def generate_keys():
    """Generate secure random keys"""
    
    print("\n" + "="*70)
    print("🔐 SETTLE Service - Security Key Generator")
    print("="*70)
    print("\nGenerating secure random keys...\n")
    
    # Generate keys
    secret_key = secrets.token_urlsafe(32)
    api_key_salt = secrets.token_urlsafe(32)
    
    # Display keys
    print("📋 Copy these to your .env.local file:\n")
    print("-"*70)
    print(f"SECRET_KEY={secret_key}")
    print(f"API_KEY_SALT={api_key_salt}")
    print("-"*70)
    
    print("\n✅ Keys generated successfully!")
    print("\n📝 Instructions:")
    print("   1. Create a file named .env.local in the project root")
    print("   2. Copy the lines above into .env.local")
    print("   3. Add your Supabase credentials (see SETUP_ENV.md)")
    print("\n⚠️  WARNING: Keep these keys secret! Never commit them to git.\n")
    print("="*70)


if __name__ == "__main__":
    generate_keys()

