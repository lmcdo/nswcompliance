-- Pipeline cache for conveyancing: stores free-tier results so the PDF
-- endpoint doesn't re-run the full pipeline.
-- Rows are ephemeral (TTL ~24h enforced by application, not DB).

CREATE TABLE IF NOT EXISTS conveyancing_cache (
    report_id  TEXT PRIMARY KEY,
    pipeline_data  JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE conveyancing_cache IS 'Short-lived cache of free-tier conveyancing pipeline results, keyed by report_id (UUID). The PDF endpoint reads from here to avoid re-fetching controls/valuation/overlays.';
