-- Migration 004 — Security & Multi-Tenancy (Sprint 9)
-- Idempotent: safe to re-run.

-- ── Organizations ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS organizations (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT         NOT NULL,
    slug        TEXT         NOT NULL,
    plan        TEXT         NOT NULL DEFAULT 'free',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_org_slug UNIQUE (slug)
);

-- Default development organization for backward-compatibility
INSERT INTO organizations (id, name, slug, plan)
VALUES ('00000000-0000-0000-0000-000000000001', 'Default Org', 'default', 'free')
ON CONFLICT DO NOTHING;

-- ── Organization members ──────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS org_members (
    id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID         NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id     TEXT         NOT NULL,   -- external provider subject (sub)
    email       TEXT         NOT NULL,
    role        TEXT         NOT NULL DEFAULT 'viewer',  -- admin | marketer | analyst | viewer
    invited_by  TEXT,
    joined_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_org_member UNIQUE (org_id, user_id)
);

CREATE INDEX IF NOT EXISTS ix_org_members_org_id ON org_members(org_id);
CREATE INDEX IF NOT EXISTS ix_org_members_user_id ON org_members(user_id);

-- ── API keys ──────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS api_keys (
    id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id       UUID         NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name         TEXT         NOT NULL,
    key_hash     TEXT         NOT NULL,   -- sha256(raw_key)
    key_prefix   TEXT         NOT NULL,   -- first 8 chars for display
    role         TEXT         NOT NULL DEFAULT 'marketer',
    expires_at   TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    created_by   TEXT         NOT NULL,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    is_active    BOOLEAN      NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_api_key_hash UNIQUE (key_hash)
);

CREATE INDEX IF NOT EXISTS ix_api_keys_org_id ON api_keys(org_id);
CREATE INDEX IF NOT EXISTS ix_api_keys_hash   ON api_keys(key_hash);

-- ── Audit events ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS audit_events (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id        UUID         REFERENCES organizations(id) ON DELETE SET NULL,
    user_id       TEXT         NOT NULL,
    email         TEXT,
    role          TEXT,
    action        TEXT         NOT NULL,   -- e.g. 'simulation.run', 'segment.create'
    resource_type TEXT,
    resource_id   TEXT,
    request_path  TEXT,
    request_method TEXT,
    request_ip    TEXT,
    user_agent    TEXT,
    status_code   INT,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_audit_events_org_id     ON audit_events(org_id);
CREATE INDEX IF NOT EXISTS ix_audit_events_user_id    ON audit_events(user_id);
CREATE INDEX IF NOT EXISTS ix_audit_events_created_at ON audit_events(created_at DESC);
CREATE INDEX IF NOT EXISTS ix_audit_events_action     ON audit_events(action);

-- ── Add org_id to existing tables ────────────────────────────────────────────

ALTER TABLE segments
    ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id) ON DELETE CASCADE;

-- Back-fill existing rows with the default org
UPDATE segments SET org_id = '00000000-0000-0000-0000-000000000001'
WHERE org_id IS NULL;

ALTER TABLE simulation_runs
    ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id) ON DELETE CASCADE;

UPDATE simulation_runs SET org_id = '00000000-0000-0000-0000-000000000001'
WHERE org_id IS NULL;

ALTER TABLE campaigns
    ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id) ON DELETE CASCADE;

UPDATE campaigns SET org_id = '00000000-0000-0000-0000-000000000001'
WHERE org_id IS NULL;
