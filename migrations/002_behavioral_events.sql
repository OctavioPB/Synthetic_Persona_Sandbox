-- Sprint 2 — behavioral_events table
-- Stores anonymized events from the Kafka ingestion pipeline.
-- Raw PII is never written here; the anonymizer layer applies before insert.

BEGIN;

CREATE TABLE IF NOT EXISTS behavioral_events (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Idempotency key — duplicate events from Kafka retries are silently dropped.
    event_id     TEXT        NOT NULL UNIQUE,
    event_type   TEXT        NOT NULL
                             CHECK (event_type IN ('page_view', 'purchase', 'session')),
    user_id_hash TEXT        NOT NULL,  -- HMAC-SHA256 of raw user_id
    session_id   TEXT        NOT NULL,
    timestamp    TIMESTAMPTZ NOT NULL,
    -- Anonymized event payload as JSONB (no PII fields)
    payload      JSONB       NOT NULL DEFAULT '{}',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_be_user_id_hash ON behavioral_events (user_id_hash);
CREATE INDEX IF NOT EXISTS idx_be_event_type   ON behavioral_events (event_type);
CREATE INDEX IF NOT EXISTS idx_be_timestamp    ON behavioral_events (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_be_session_id   ON behavioral_events (session_id);

COMMIT;
