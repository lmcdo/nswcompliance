-- Migration 007: DCP Chapter Registry
-- Tracks individual chapter PDFs for each council DCP.
-- Each row = one chapter PDF with its canonical council URL and R2 storage path.
-- The weekly monitor polls council_url and detects changes via content hash.
--
-- Run with:
--   psql $DATABASE_URL -f migrations/007_dcp_chapter_registry.sql

BEGIN;

CREATE TABLE IF NOT EXISTS dcp_chapter_registry (
    id                   SERIAL PRIMARY KEY,

    -- Document identity
    council              TEXT NOT NULL,              -- 'marrickville' | 'leichhardt' | 'ashfield'
    dcp_name             TEXT NOT NULL,              -- 'Marrickville DCP 2011'
    doc_type             TEXT NOT NULL DEFAULT 'dcp', -- 'dcp' | 'lep' | 'sepp' | 'adg' | 'map'
    chapter_key          TEXT NOT NULL,              -- stable slug, e.g. 'part2-s10-parking'
    chapter_label        TEXT,                       -- human label, e.g. 'Part 2 · 2.10 · Parking'
    sort_order           INTEGER,                    -- for display ordering within council

    -- Source URL (council website or NSW Legislation)
    council_url          TEXT,                       -- full URL to download PDF from
    council_page_url     TEXT,                       -- parent page URL (for monitoring page changes)

    -- R2 storage
    r2_current_path      TEXT,                       -- 'source-pdfs/dcps/marrickville/v1.0-baseline/part2-s10-parking.pdf'
    r2_version_label     TEXT DEFAULT 'v1.0-baseline',

    -- Change detection (updated on every monitor check)
    content_hash         TEXT,                       -- SHA-256 of PDF content (primary change detector)
    url_content_length   BIGINT,                     -- Content-Length from HTTP response (quick pre-check)
    url_etag             TEXT,                       -- ETag header if server provides one
    url_last_modified    TEXT,                       -- Last-Modified header if server provides one
    url_last_checked     TIMESTAMPTZ,                -- when monitor last polled this URL
    url_last_changed     TIMESTAMPTZ,                -- when monitor last detected a content change
    check_failures       INTEGER DEFAULT 0,          -- consecutive download failures (alert if >3)

    -- Page range in assembled DCP (populated after extraction)
    -- NULL until first extraction run
    page_start           INTEGER,                    -- first global page number in assembled DCP
    page_end             INTEGER,                    -- last global page number

    -- Status
    is_active            BOOLEAN DEFAULT TRUE,       -- false = URL dead or chapter removed from DCP
    needs_extraction     BOOLEAN DEFAULT FALSE,      -- set TRUE when content_hash changes
    notes                TEXT,

    created_at           TIMESTAMPTZ DEFAULT NOW(),
    updated_at           TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE (council, chapter_key)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_dcr_council       ON dcp_chapter_registry (council);
CREATE INDEX IF NOT EXISTS idx_dcr_doc_type      ON dcp_chapter_registry (doc_type);
CREATE INDEX IF NOT EXISTS idx_dcr_active        ON dcp_chapter_registry (is_active) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_dcr_last_checked  ON dcp_chapter_registry (url_last_checked);
CREATE INDEX IF NOT EXISTS idx_dcr_needs_extract ON dcp_chapter_registry (needs_extraction) WHERE needs_extraction = TRUE;

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION _update_dcp_chapter_registry_ts()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_dcr_updated_at ON dcp_chapter_registry;
CREATE TRIGGER trg_dcr_updated_at
    BEFORE UPDATE ON dcp_chapter_registry
    FOR EACH ROW EXECUTE FUNCTION _update_dcp_chapter_registry_ts();

COMMIT;
