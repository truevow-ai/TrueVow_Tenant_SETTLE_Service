-- =============================================================================
-- Auth Audit Log Table
-- Per TrueVow Security Contract v1
-- =============================================================================

CREATE TABLE IF NOT EXISTS settle_auth_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    tenant_id TEXT,
    clerk_user_id VARCHAR(255),
    endpoint VARCHAR(500) NOT NULL,
    method VARCHAR(10) NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    auth_method VARCHAR(20),
    scope VARCHAR(20),
    permission_checked VARCHAR(100),
    response_status INTEGER,
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_auth_audit_tenant ON settle_auth_audit_log(tenant_id);
CREATE INDEX IF NOT EXISTS idx_auth_audit_user ON settle_auth_audit_log(clerk_user_id);
CREATE INDEX IF NOT EXISTS idx_auth_audit_request ON settle_auth_audit_log(request_id);
CREATE INDEX IF NOT EXISTS idx_auth_audit_event ON settle_auth_audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_auth_audit_endpoint ON settle_auth_audit_log(endpoint);
CREATE INDEX IF NOT EXISTS idx_auth_audit_created ON settle_auth_audit_log(created_at);

ALTER TABLE settle_auth_audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Auth audit - service full"
ON settle_auth_audit_log FOR ALL
TO service_role
USING (true)
WITH CHECK (true);
