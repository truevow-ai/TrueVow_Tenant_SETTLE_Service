-- =============================================================================
-- Migration: Add tenant_id support for Customer Portal Integration
-- Date: 2026-03-02
-- Includes: Audit columns per TrueVow standards
-- =============================================================================

-- Step 1: Add tenant_id column to existing settle_api_keys table
ALTER TABLE settle_api_keys 
ADD COLUMN IF NOT EXISTS tenant_id TEXT;

-- Step 2: Add audit columns to settle_api_keys (if not already added by audit migration)
ALTER TABLE settle_api_keys
ADD COLUMN IF NOT EXISTS created_by UUID,
ADD COLUMN IF NOT EXISTS updated_by UUID,
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS deleted_by UUID,
ADD COLUMN IF NOT EXISTS row_version INTEGER NOT NULL DEFAULT 1;

-- Step 3: Create index for tenant lookups
CREATE INDEX IF NOT EXISTS idx_settle_api_keys_tenant_id 
ON settle_api_keys(tenant_id);

-- Step 4: Create index for active tenant keys
CREATE INDEX IF NOT EXISTS idx_settle_api_keys_tenant_active 
ON settle_api_keys(tenant_id, is_active) 
WHERE is_active = true;

-- Step 5: Create index for deleted_at
CREATE INDEX IF NOT EXISTS idx_settle_api_keys_deleted_at 
ON settle_api_keys(deleted_at) 
WHERE deleted_at IS NULL;

-- Step 6: Create tenant-scoped API keys table
CREATE TABLE IF NOT EXISTS settle_tenant_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    api_key_hash VARCHAR(255) NOT NULL,
    access_level VARCHAR(50) DEFAULT 'standard',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by UUID,
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    row_version INTEGER NOT NULL DEFAULT 1,
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    description VARCHAR(500),
    UNIQUE(tenant_id, api_key_hash)
);

-- Step 7: Indexes for tenant API keys
CREATE INDEX IF NOT EXISTS idx_settle_tenant_keys_tenant ON settle_tenant_api_keys(tenant_id);
CREATE INDEX IF NOT EXISTS idx_settle_tenant_keys_hash ON settle_tenant_api_keys(api_key_hash);

-- Step 8: Create service keys table
CREATE TABLE IF NOT EXISTS settle_service_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_name VARCHAR(100) NOT NULL UNIQUE,
    api_key_hash VARCHAR(255) NOT NULL,
    internal_role VARCHAR(50) DEFAULT 'service',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    updated_by UUID,
    deleted_at TIMESTAMPTZ,
    deleted_by UUID,
    row_version INTEGER NOT NULL DEFAULT 1,
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    description VARCHAR(500),
    UNIQUE(service_name, api_key_hash)
);

-- Step 9: Indexes for service keys
CREATE INDEX IF NOT EXISTS idx_settle_service_keys_name ON settle_service_keys(service_name);
CREATE INDEX IF NOT EXISTS idx_settle_service_keys_hash ON settle_service_keys(api_key_hash);

-- Step 10: Enable RLS
ALTER TABLE settle_tenant_api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE settle_service_keys ENABLE ROW LEVEL SECURITY;

-- Done
