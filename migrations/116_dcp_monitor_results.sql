-- 116: record every dcp-monitor run, every council list it read, every chapter it checked.
--
-- WHY
-- ---
-- Nothing stored a run's outcome. r2_monitor overwrote dcp_chapter_registry.url_last_checked and
-- printed the rest, so "was this chapter really checked, and how" had no answer in the database,
-- and a chapter rate-limited twice was skipped with no record at all (v6 finding 13).
-- The daily alarm (scripts/verifyops_coverage.py) reads these tables.
--
-- prior-art-checked: no dcp_monitor_* table exists (information_schema, 2026-10-22). The only
-- run-like table is data_source_health_checks (043), keyed per external API endpoint, not per
-- document. Spec: ~/.claude/plans/ce-verifyops-v5-SPEC-2026-10-22.md, v6 resolutions 3-5, 9, 12, 13.
--
-- SIZE: ~570 chapter rows + ~21 council rows a day, ~210k rows a year. Small; no pruning yet.
--
-- Rollback:
--   DROP TABLE dcp_monitor_chapter_results, dcp_monitor_council_results, dcp_monitor_runs;
--   ALTER TABLE dcp_chapter_registry DROP COLUMN url_last_downloaded;
-- (r2_monitor treats a missing url_last_downloaded as "never", so it only downloads more.)
--
-- VERIFY
--   SELECT count(*) FROM information_schema.tables WHERE table_name LIKE 'dcp_monitor_%';  -- 3

BEGIN;

CREATE TABLE IF NOT EXISTS dcp_monitor_runs (
    id           BIGSERIAL PRIMARY KEY,
    started_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at  TIMESTAMPTZ,              -- NULL = the run died before the end
    mode         TEXT NOT NULL,            -- 'daily' | 'force' | 'council:<slug>'
    git_sha      TEXT,                     -- RAILWAY_GIT_COMMIT_SHA of the code that ran
    summary      JSONB
);

CREATE TABLE IF NOT EXISTS dcp_monitor_council_results (
    id                BIGSERIAL PRIMARY KEY,
    run_id            BIGINT NOT NULL REFERENCES dcp_monitor_runs(id),
    council           TEXT NOT NULL,
    page_url          TEXT,
    outcome           TEXT NOT NULL CHECK (outcome IN ('ok','blocked','empty','error','anomaly','no_scraper')),
    link_count        INT NOT NULL DEFAULT 0,
    list_fingerprint  TEXT,
    links             JSONB NOT NULL DEFAULT '[]'::jsonb,  -- [{href, norm, base, text, chapter_key}]
    alerts            JSONB NOT NULL DEFAULT '[]'::jsonb,  -- lines raised (or, in shadow week, logged)
    detail            TEXT,
    checked_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_dmcr_council_ok ON dcp_monitor_council_results (council, id DESC)
    WHERE outcome = 'ok';

CREATE TABLE IF NOT EXISTS dcp_monitor_chapter_results (
    id           BIGSERIAL PRIMARY KEY,
    run_id       BIGINT NOT NULL REFERENCES dcp_monitor_runs(id),
    chapter_id   INT NOT NULL,             -- dcp_chapter_registry.id (no FK: rows are never deleted, but keep history if one is)
    council      TEXT NOT NULL,
    chapter_key  TEXT NOT NULL,
    outcome      TEXT NOT NULL CHECK (outcome IN (
                     'unchanged_etag','unchanged_hash','unchanged_head','reexport','changed','etag_lied',
                     'no_url','waf_blocked','rate_limited','transient','failed')),
    reason       TEXT,                     -- why it downloaded or not (verifyops_record.decide_fetch)
    detail       TEXT,
    checked_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_dmchr_chapter ON dcp_monitor_chapter_results (chapter_id, id DESC);

-- When the file was last downloaded in full (not just HEAD). Untagged files are downloaded weekly.
ALTER TABLE dcp_chapter_registry ADD COLUMN IF NOT EXISTS url_last_downloaded TIMESTAMPTZ;

COMMIT;
