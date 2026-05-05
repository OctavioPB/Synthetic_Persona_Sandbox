-- Sprint 1 — PostgreSQL schema v1
-- Tables: users, segments, simulation_runs

BEGIN;

-- ── Users ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT NOT NULL UNIQUE,
    full_name   TEXT,
    org_id      UUID,
    role        TEXT NOT NULL DEFAULT 'marketer'
                    CHECK (role IN ('admin', 'marketer', 'analyst', 'viewer')),
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email   ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_org_id  ON users (org_id);

-- ── Segments ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS segments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL,
    name            TEXT NOT NULL,
    description     TEXT,
    -- Segment definition: stored as JSONB for flexibility
    -- Expected structure: { age_range, geo, category_affinities, purchase_history_days }
    definition      JSONB NOT NULL DEFAULT '{}',
    -- Embedding reference in Qdrant (collection + vector id)
    qdrant_id       TEXT,
    embedding_model TEXT,
    is_stale        BOOLEAN NOT NULL DEFAULT FALSE,
    last_trained_at TIMESTAMPTZ,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_segments_org_id ON segments (org_id);
CREATE INDEX IF NOT EXISTS idx_segments_name   ON segments (org_id, name);

-- ── Simulation runs ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS simulation_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id          UUID NOT NULL,
    segment_id      UUID NOT NULL REFERENCES segments(id) ON DELETE CASCADE,
    triggered_by    UUID REFERENCES users(id) ON DELETE SET NULL,
    -- Stimulus: the campaign input sent to the persona
    -- Expected structure: { type: 'ad_copy'|'price_change'|'promo', content: ... }
    stimulus        JSONB NOT NULL,
    -- Results populated after the simulation completes
    status          TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    conversion_score NUMERIC(5, 4),           -- 0.0000 – 1.0000
    synthetic_response TEXT,
    error_message   TEXT,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sim_runs_org_id     ON simulation_runs (org_id);
CREATE INDEX IF NOT EXISTS idx_sim_runs_segment_id ON simulation_runs (segment_id);
CREATE INDEX IF NOT EXISTS idx_sim_runs_status     ON simulation_runs (status);
CREATE INDEX IF NOT EXISTS idx_sim_runs_created_at ON simulation_runs (created_at DESC);

-- ── updated_at trigger ─────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE TRIGGER trg_segments_updated_at
    BEFORE UPDATE ON segments
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE TRIGGER trg_sim_runs_updated_at
    BEFORE UPDATE ON simulation_runs
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMIT;
