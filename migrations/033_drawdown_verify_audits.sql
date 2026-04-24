-- Migration 033: drawdown_verify_audits
-- Immutable audit log for construction loan drawdown verifications.
-- Every verification request is stored before the result is returned.
-- This is legal evidence if construction fraud goes to court.
--
-- Run: psql $DATABASE_URL -f migrations/033_drawdown_verify_audits.sql

CREATE TABLE IF NOT EXISTS drawdown_verify_audits (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Lender-supplied inputs (do not store borrower name or PII beyond address + loan ref)
    loan_id              TEXT NOT NULL,
    address              TEXT NOT NULL,
    stage_claimed        TEXT NOT NULL
                           CHECK (stage_claimed IN ('site_cleared','slab','frame','lock_up','completion')),

    -- HyP3 job tracking
    hyp3_job_name        TEXT NOT NULL,
    hyp3_job_id          TEXT,

    -- Sentinel-1 scene IDs used for the coherence pair
    scene_before         TEXT,
    scene_after          TEXT,

    -- Job lifecycle
    status               TEXT NOT NULL DEFAULT 'submitted'
                           CHECK (status IN ('submitted','processing','complete','failed')),

    -- Result (populated on completion)
    confidence           FLOAT CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1)),
    coherence_delta      FLOAT,   -- after - before; negative = construction activity detected
    coherence_before     FLOAT,
    coherence_after      FLOAT,
    evidence_date_before TEXT,    -- YYYY-MM-DD of scene_before acquisition
    evidence_date_after  TEXT,    -- YYYY-MM-DD of scene_after acquisition

    manual_review        BOOLEAN,
    geotiff_r2_key       TEXT,    -- R2 object key for the stored coherence GeoTIFF
    error_message        TEXT,

    created_at           TIMESTAMPTZ DEFAULT NOW(),
    updated_at           TIMESTAMPTZ DEFAULT NOW()
);

-- Index for lender-facing lookups (loan_id → all verifications for a loan)
CREATE INDEX IF NOT EXISTS idx_drawdown_verify_loan_id
    ON drawdown_verify_audits (loan_id);

-- Index for job status polling
CREATE INDEX IF NOT EXISTS idx_drawdown_verify_status
    ON drawdown_verify_audits (status)
    WHERE status IN ('submitted', 'processing');

COMMENT ON TABLE drawdown_verify_audits IS
    'Immutable audit log for satellite-based construction loan drawdown verifications. '
    'Every API call is recorded before the result is returned. '
    'GeoTIFF evidence is stored in R2 at the key in geotiff_r2_key.';
