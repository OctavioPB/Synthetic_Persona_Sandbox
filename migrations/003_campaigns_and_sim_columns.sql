-- Sprint 5 — campaigns, campaign_variants, and simulation_runs column additions
-- Safe to re-run: all changes use IF NOT EXISTS / ADD COLUMN IF NOT EXISTS.

BEGIN;

-- ── Simulation runs — add Sprint 4 columns ────────────────────────────────
-- S4 ORM added columns not present in the original 001 schema.

ALTER TABLE simulation_runs
    ADD COLUMN IF NOT EXISTS verbatim_response    TEXT,
    ADD COLUMN IF NOT EXISTS sentiment            TEXT
                                 CHECK (sentiment IN ('positive', 'neutral', 'negative')),
    ADD COLUMN IF NOT EXISTS likelihood_to_convert NUMERIC(5, 4),
    ADD COLUMN IF NOT EXISTS llm_metadata         JSONB NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS model_id             TEXT;

-- Index for filtering by status + created_at already exists from 001.
-- Add sentiment index for analytics queries.
CREATE INDEX IF NOT EXISTS idx_sim_runs_sentiment ON simulation_runs (sentiment);

-- ── Campaigns ─────────────────────────────────────────────────────────────
-- A campaign groups one or more ad variants to be competed against a segment.

CREATE TABLE IF NOT EXISTS campaigns (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id      UUID NOT NULL,
    segment_id  UUID REFERENCES segments(id) ON DELETE SET NULL,
    name        TEXT NOT NULL,
    description TEXT,
    status      TEXT NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft', 'running', 'completed', 'archived')),
    created_by  UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_campaigns_org_id     ON campaigns (org_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_segment_id ON campaigns (segment_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_status     ON campaigns (status);

CREATE OR REPLACE TRIGGER trg_campaigns_updated_at
    BEFORE UPDATE ON campaigns
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ── Campaign variants ──────────────────────────────────────────────────────
-- Each variant holds one stimulus (ad copy, price change, or promo).
-- rank and score are populated by the variant_competition DAG.

CREATE TABLE IF NOT EXISTS campaign_variants (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    -- Full stimulus object; type discriminated by the 'type' field
    stimulus    JSONB NOT NULL DEFAULT '{}',
    -- Populated after variant_competition DAG completes
    rank        INT,
    score       NUMERIC(5, 4),
    run_id      UUID REFERENCES simulation_runs(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_variants_campaign_id ON campaign_variants (campaign_id);
CREATE INDEX IF NOT EXISTS idx_variants_rank        ON campaign_variants (campaign_id, rank);

CREATE OR REPLACE TRIGGER trg_variants_updated_at
    BEFORE UPDATE ON campaign_variants
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMIT;
