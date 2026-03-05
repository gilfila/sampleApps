-- Migration 006: MFA (Multi-Factor Authentication) tables
-- Adds user_mfa, trusted_devices, mfa_audit_log, and app_settings tables
-- for TOTP-based multi-factor authentication. Idempotent for safe re-runs.

-- User MFA configuration
CREATE TABLE IF NOT EXISTS user_mfa (
    user_id INTEGER PRIMARY KEY REFERENCES workers(id) ON DELETE CASCADE,
    totp_secret_encrypted BYTEA NOT NULL,
    totp_secret_nonce BYTEA NOT NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    backup_codes JSON NOT NULL DEFAULT '[]',
    backup_codes_remaining INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Trusted devices
CREATE TABLE IF NOT EXISTS trusted_devices (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    device_token_hash VARCHAR(128) NOT NULL,
    user_agent VARCHAR(500),
    ip_address VARCHAR(45),
    last_used_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trusted_devices_user ON trusted_devices(user_id);
CREATE INDEX IF NOT EXISTS idx_trusted_devices_token ON trusted_devices(device_token_hash);
CREATE INDEX IF NOT EXISTS idx_trusted_devices_expires ON trusted_devices(expires_at);

-- MFA audit log
CREATE TABLE IF NOT EXISTS mfa_audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    details JSON,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mfa_audit_user ON mfa_audit_log(user_id);
CREATE INDEX IF NOT EXISTS idx_mfa_audit_action ON mfa_audit_log(action);
CREATE INDEX IF NOT EXISTS idx_mfa_audit_created ON mfa_audit_log(created_at);

-- App-wide settings
CREATE TABLE IF NOT EXISTS app_settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSON NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_by INTEGER REFERENCES workers(id)
);

-- Seed MFA enforcement setting
INSERT INTO app_settings (key, value, updated_at) VALUES ('mfa_enforcement', '"optional"', NOW())
ON CONFLICT (key) DO NOTHING;
