-- Migration 042: Report Audit Trail + Disclaimer Versioning
-- Purpose: Legal defensibility infrastructure for satellite product reports.
--          Proves what data was used, what code processed it, and what disclaimer
--          was shown — for the life of the product plus 10-year limitation period.
-- Date: 2026-05-18
-- Related: docs/qa/language-audit-2026-05-18.md, ~/.claude/plans/ce-satellite-qa-validation-plan.md

-- ============================================================================
-- Table 1: report_audit_trail
-- Append-only log of every report generation. One row per report.
-- No UPDATE or DELETE — immutability is the legal requirement.
-- ============================================================================

CREATE TABLE IF NOT EXISTS report_audit_trail (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id       UUID NOT NULL,
    pipeline_name   TEXT NOT NULL,        -- 'bushfire' | 'solar-yield' | 'flood' | 'shadow' | 'granny-flat' | 'threat-radar' | 'pre-da-history' | 'climate-risk'
    pipeline_version TEXT NOT NULL,       -- git commit SHA at deploy time
    input_params    JSONB NOT NULL,       -- address, lat, lng, lot_geometry, etc.
    data_sources_queried JSONB NOT NULL,  -- array of { source_name, url, query_timestamp, response_hash, features_returned, cache_hit }
    intermediate_calculations JSONB,      -- optional: key calc steps for algorithm traceability
    output_summary  JSONB NOT NULL,       -- the outputs JSON written to property_reports
    disclaimer_version TEXT NOT NULL,     -- version string of disclaimer shown (e.g. 'bushfire-v1')
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for looking up audit trail by report
CREATE INDEX IF NOT EXISTS idx_audit_trail_report_id ON report_audit_trail (report_id);

-- Index for pipeline-level queries (e.g. "show all bushfire audits this month")
CREATE INDEX IF NOT EXISTS idx_audit_trail_pipeline_date ON report_audit_trail (pipeline_name, created_at DESC);

-- Comment explaining the append-only policy
COMMENT ON TABLE report_audit_trail IS
    'Append-only audit log for satellite product reports. '
    'DO NOT add UPDATE or DELETE policies. Immutability is required for legal defensibility. '
    'Retention: 10 years (Design and Building Practitioners Act 2020 limitation period).';


-- ============================================================================
-- Table 2: disclaimer_versions
-- Tracks what disclaimer text was active for each product at each point in time.
-- Proves what the user was shown when they received their report.
-- ============================================================================

CREATE TABLE IF NOT EXISTS disclaimer_versions (
    id              SERIAL PRIMARY KEY,
    pipeline_name   TEXT NOT NULL,         -- matches report_audit_trail.pipeline_name
    version         TEXT NOT NULL,         -- e.g. 'bushfire-v1', 'flood-v2'
    headline_disclaimer TEXT NOT NULL,     -- short disclaimer shown prominently on report
    limitations_text TEXT NOT NULL,        -- specific limitations for this product
    source_attributions TEXT NOT NULL,     -- data source names + their own disclaimers
    effective_from  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    superseded_at   TIMESTAMPTZ,          -- NULL = currently active
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (pipeline_name, version)
);

-- Index for looking up current active disclaimer per pipeline
CREATE INDEX IF NOT EXISTS idx_disclaimer_active ON disclaimer_versions (pipeline_name, effective_from DESC)
    WHERE superseded_at IS NULL;

COMMENT ON TABLE disclaimer_versions IS
    'Versioned disclaimer text per product. Each report_audit_trail row references a disclaimer version. '
    'When disclaimers change, insert a new row and set superseded_at on the old one. Never delete rows.';
