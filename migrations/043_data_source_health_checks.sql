-- Migration 043: Data Source Health Checks
-- Purpose: Track availability, response time, and schema stability of all
--          external data sources used by satellite product pipelines.
--          Part of QA defensibility infrastructure — proves ongoing monitoring
--          of data source reliability (ACL s18 reasonable care, Shaddock duty).
-- Date: 2026-05-20
-- Related: docs/QA-DATA-PROVENANCE.md, migrations/042_report_audit_trail.sql

-- ============================================================================
-- Table: data_source_health_checks
-- Append-only log of automated health probes against external APIs.
-- One row per source per check run. Never updated or deleted.
-- ============================================================================

CREATE TABLE IF NOT EXISTS data_source_health_checks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id          UUID NOT NULL,             -- groups all checks from a single run
    source_key      TEXT NOT NULL,             -- stable identifier (e.g. 'rfs_bfpl', 'google_solar')
    source_name     TEXT NOT NULL,             -- human-readable name
    endpoint_url    TEXT NOT NULL,             -- URL that was probed
    pipeline_names  TEXT[] NOT NULL,           -- which pipelines depend on this source
    status          TEXT NOT NULL,             -- 'ok' | 'degraded' | 'down' | 'schema_changed' | 'stale'
    http_status     INTEGER,                   -- HTTP response code (NULL if connection failed)
    response_time_ms INTEGER,                  -- round-trip time in milliseconds
    response_hash   TEXT,                      -- SHA-256 of response body (detect schema drift)
    schema_valid    BOOLEAN,                   -- did response match expected structure?
    error_message   TEXT,                      -- error detail if not 'ok'
    metadata        JSONB,                     -- source-specific details (feature count, data date, etc.)
    checked_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for dashboard queries: "show me the latest check for each source"
CREATE INDEX IF NOT EXISTS idx_health_checks_source_date
    ON data_source_health_checks (source_key, checked_at DESC);

-- Index for run-level queries: "show all results from this run"
CREATE INDEX IF NOT EXISTS idx_health_checks_run_id
    ON data_source_health_checks (run_id);

-- Index for alerting: "find all recent failures"
CREATE INDEX IF NOT EXISTS idx_health_checks_status
    ON data_source_health_checks (status, checked_at DESC)
    WHERE status != 'ok';

COMMENT ON TABLE data_source_health_checks IS
    'Append-only log of external data source health probes for satellite pipelines. '
    'DO NOT add UPDATE or DELETE policies. Immutability supports QA defensibility. '
    'Retention: aligned with report_audit_trail (10 years).';
