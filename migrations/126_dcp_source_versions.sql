-- 126: a dated, append-only ledger of every council source file we have held, so "which council text applied on date D" has an answer.
--
-- WHY. Council PDFs are replaced silently. r2_monitor already stores every new version under a NEW path and never deletes
-- (803 files since 2026-02-28 at 2026-11-18), but nothing recorded WHEN each file was held, so the history could not be asked
-- for by date. Certifier law is moving (Building (Approvals and Practitioners) Bill 2026) and dated evidence cannot be rebuilt later.
-- Plan: ~/.claude/plans/ce-dated-archive-PLAN-2026-11-18.md (approved by the owner 2026-11-18).
--
-- WHAT. New objects only; no existing row or column changes.
--   dcp_source_versions        append-only ledger, one row per (R2 file, event). Events:
--                                'stored'   file in R2 from captured_at (backfilled from the R2 listing, LastModified)
--                                'received' a new council file was staged (dcp_chapter_registry.staged_r2_path set)
--                                'live'     a file became the served source (dcp_chapter_registry.r2_current_path changed)
--   trigger on dcp_chapter_registry logs 'received' and 'live' for every writer, and can never block the write.
--   dcp_source_versions_dated  view adding superseded_at.   dcp_source_as_at()  the file held at a given moment.
--
-- LIMITS (state with any use). captured_at is when OUR copy was stored, NOT the date the council published it. Nothing exists before
-- 2026-02-28. etag is the R2 ETag (MD5 for single-part uploads), not sha256. Legislation text and map layers are not covered.

BEGIN;

CREATE TABLE IF NOT EXISTS dcp_source_versions (
    id             bigserial   PRIMARY KEY,
    council        text        NOT NULL,
    chapter_key    text        NOT NULL,
    version_label  text        NOT NULL,
    r2_key         text        NOT NULL,
    event          text        NOT NULL CHECK (event IN ('stored', 'received', 'live')),
    size_bytes     bigint,
    etag           text,
    content_hash   text,
    captured_at    timestamptz NOT NULL,
    source         text        NOT NULL CHECK (source IN ('r2_listing_backfill', 'registry_trigger')),
    recorded_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (r2_key, event)
);

CREATE INDEX IF NOT EXISTS dcp_source_versions_chapter_time
    ON dcp_source_versions (council, chapter_key, captured_at);

COMMENT ON TABLE dcp_source_versions IS
  'Append-only ledger of council source files we have held. captured_at = when OUR copy was stored, not the council publication date. See migration 126.';

-- Evidence must not be editable: refuse UPDATE, DELETE and TRUNCATE. (Drop the guard triggers first if a repair is ever justified.)
CREATE OR REPLACE FUNCTION dcp_source_versions_append_only() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'dcp_source_versions is append-only: % refused', TG_OP;
END;
$$;

DROP TRIGGER IF EXISTS dcp_source_versions_no_change ON dcp_source_versions;
CREATE TRIGGER dcp_source_versions_no_change
    BEFORE UPDATE OR DELETE ON dcp_source_versions
    FOR EACH ROW EXECUTE FUNCTION dcp_source_versions_append_only();

DROP TRIGGER IF EXISTS dcp_source_versions_no_truncate ON dcp_source_versions;
CREATE TRIGGER dcp_source_versions_no_truncate
    BEFORE TRUNCATE ON dcp_source_versions
    FOR EACH STATEMENT EXECUTE FUNCTION dcp_source_versions_append_only();

-- Not readable through the public API key. Server connections (table owner) are unaffected.
ALTER TABLE dcp_source_versions ENABLE ROW LEVEL SECURITY;

-- Logging can never block the monitor or an intake: any failure inside is turned into a warning.
CREATE OR REPLACE FUNCTION dcp_registry_log_source_version() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    BEGIN
        IF NEW.r2_current_path IS NOT NULL
           AND (TG_OP = 'INSERT' OR NEW.r2_current_path IS DISTINCT FROM OLD.r2_current_path) THEN
            INSERT INTO dcp_source_versions
                (council, chapter_key, version_label, r2_key, event, size_bytes, content_hash, captured_at, source)
            VALUES
                (NEW.council, NEW.chapter_key,
                 COALESCE(NEW.r2_version_label, split_part(NEW.r2_current_path, '/', 4)),
                 NEW.r2_current_path, 'live', NEW.url_content_length, NEW.content_hash, now(), 'registry_trigger')
            ON CONFLICT (r2_key, event) DO NOTHING;
        END IF;
        IF NEW.staged_r2_path IS NOT NULL
           AND (TG_OP = 'INSERT' OR NEW.staged_r2_path IS DISTINCT FROM OLD.staged_r2_path) THEN
            INSERT INTO dcp_source_versions
                (council, chapter_key, version_label, r2_key, event, size_bytes, content_hash, captured_at, source)
            VALUES
                (NEW.council, NEW.chapter_key,
                 COALESCE(NEW.staged_version_label, split_part(NEW.staged_r2_path, '/', 4)),
                 NEW.staged_r2_path, 'received', NEW.staged_url_content_length, NEW.staged_content_hash,
                 COALESCE(NEW.staged_at, now()), 'registry_trigger')
            ON CONFLICT (r2_key, event) DO NOTHING;
        END IF;
    EXCEPTION WHEN OTHERS THEN
        RAISE WARNING 'dcp_source_versions: could not log % %: %', NEW.council, NEW.chapter_key, SQLERRM;
    END;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS dcp_registry_log_source_version ON dcp_chapter_registry;
CREATE TRIGGER dcp_registry_log_source_version
    AFTER INSERT OR UPDATE OF r2_current_path, staged_r2_path ON dcp_chapter_registry
    FOR EACH ROW EXECUTE FUNCTION dcp_registry_log_source_version();

CREATE OR REPLACE VIEW dcp_source_versions_dated AS
SELECT v.*,
       lead(v.captured_at) OVER (PARTITION BY v.council, v.chapter_key, v.event ORDER BY v.captured_at, v.id) AS superseded_at
FROM dcp_source_versions v;

-- The file we held for a chapter at a moment: the latest 'stored' or 'received' row at or before p_at. NULL result = nothing recorded then.
CREATE OR REPLACE FUNCTION dcp_source_as_at(
    p_council text, p_chapter_key text, p_at timestamptz,
    p_events text[] DEFAULT ARRAY['stored', 'received']
) RETURNS SETOF dcp_source_versions
LANGUAGE sql STABLE AS $$
    SELECT * FROM dcp_source_versions
    WHERE council = p_council AND chapter_key = p_chapter_key
      AND event = ANY (p_events) AND captured_at <= p_at
    ORDER BY captured_at DESC, id DESC
    LIMIT 1;
$$;

COMMIT;
