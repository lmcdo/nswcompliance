-- 121: every write to a rule's words, numbers, page or proof says which pipeline run made it.
--
-- WHY. On 2026-10-29 and 2026-11-02, 122 setback rule rows were rewritten by
-- throwaway scratchpad scripts (batches 1-5) and released. Migration 120 holds any row whose
-- quote_status is not 'verbatim', but it believes whatever status the writer sends, so a
-- script that stamps 'verbatim' itself passes. Every connection is the same `postgres` user
-- (Railway included), so the database cannot tell the pipeline from a scratchpad by role.
--
-- WHAT. A pipeline script tags its connection:
--     SELECT set_config('app.pipeline_run', '<script>@<git sha>:<uuid>', false)
-- (scripts/pipeline_run.py). This trigger writes one rule_write_log row per changed row,
-- naming the protected columns that changed and the run. In mode 'enforce' it also REFUSES a
-- change to a protected column when no run is set.
--
-- SHIPS IN 'record'. 137 script files write these tables; about 14 are the pipeline. Refusing
-- untagged writes on day one would break the rest without knowing which matter. Switch with
--     UPDATE rule_write_guard SET mode = 'enforce';
-- only once `SELECT count(*) FROM rule_write_log WHERE run_id IS NULL AND at > now() - '7 days'`
-- is 0 for writes the pipeline makes.
--
-- FAILS CLOSED. If the rule_write_guard row is missing, the mode reads as 'enforce'.
--
-- LIMIT. A superuser can disable triggers or set the variable by hand. This catches accidents
-- and leaves a record; it is not access control.

CREATE TABLE IF NOT EXISTS rule_write_guard (
    one   boolean PRIMARY KEY DEFAULT true CHECK (one),
    mode  text NOT NULL DEFAULT 'record' CHECK (mode IN ('record', 'enforce'))
);
INSERT INTO rule_write_guard (one, mode) VALUES (true, 'record') ON CONFLICT (one) DO NOTHING;

CREATE TABLE IF NOT EXISTS rule_write_log (
    id          bigserial PRIMARY KEY,
    at          timestamptz NOT NULL DEFAULT now(),
    table_name  text NOT NULL,
    row_id      bigint,
    op          text NOT NULL,
    columns     text[] NOT NULL,
    run_id      text,
    db_user     text NOT NULL DEFAULT current_user,
    app_name    text DEFAULT current_setting('application_name', true)
);
CREATE INDEX IF NOT EXISTS rule_write_log_untagged ON rule_write_log (at) WHERE run_id IS NULL;
CREATE INDEX IF NOT EXISTS rule_write_log_row ON rule_write_log (table_name, row_id);

-- TG_ARGV = the protected column names for this table.
CREATE OR REPLACE FUNCTION rule_write_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    run      text := nullif(current_setting('app.pipeline_run', true), '');
    changed  text[] := '{}';
    col      text;
    new_j    jsonb;
    old_j    jsonb;
BEGIN
    IF TG_OP = 'DELETE' THEN
        new_j := to_jsonb(OLD);           -- a removed rule is logged by the row it was
    ELSE
        new_j := to_jsonb(NEW);
    END IF;
    IF TG_OP = 'UPDATE' THEN
        old_j := to_jsonb(OLD);
        FOREACH col IN ARRAY TG_ARGV LOOP
            IF (new_j -> col) IS DISTINCT FROM (old_j -> col) THEN
                changed := changed || col;
            END IF;
        END LOOP;
    ELSE
        changed := TG_ARGV;
    END IF;

    IF cardinality(changed) = 0 THEN
        RETURN NEW;                       -- nothing protected changed (UPDATE only)
    END IF;

    IF run IS NULL AND coalesce((SELECT mode FROM rule_write_guard), 'enforce') = 'enforce' THEN
        RAISE EXCEPTION 'rule_write_guard: % row % on % changes % with no pipeline run (set app.pipeline_run via scripts/pipeline_run.py)',
            TG_OP, (new_j ->> 'id'), TG_TABLE_NAME, changed
            USING ERRCODE = 'insufficient_privilege';
    END IF;

    INSERT INTO rule_write_log (table_name, row_id, op, columns, run_id)
    VALUES (TG_TABLE_NAME, (new_j ->> 'id')::bigint, TG_OP, changed, run);
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;

-- TRUNCATE has no rows: one log line for the whole table, refused the same way.
CREATE OR REPLACE FUNCTION rule_write_guard_truncate() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    run text := nullif(current_setting('app.pipeline_run', true), '');
BEGIN
    IF run IS NULL AND coalesce((SELECT mode FROM rule_write_guard), 'enforce') = 'enforce' THEN
        RAISE EXCEPTION 'rule_write_guard: TRUNCATE % with no pipeline run', TG_TABLE_NAME
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    INSERT INTO rule_write_log (table_name, row_id, op, columns, run_id)
    VALUES (TG_TABLE_NAME, NULL, 'TRUNCATE', '{*}', run);
    RETURN NULL;
END;
$$;

-- Named zz_ so it runs after the BEFORE triggers that adjust NEW (120's hold) and logs the
-- values actually written.
DROP TRIGGER IF EXISTS zz_rule_write_guard ON dcp_setback_controls;
CREATE TRIGGER zz_rule_write_guard BEFORE INSERT OR UPDATE OR DELETE ON dcp_setback_controls
    FOR EACH ROW EXECUTE FUNCTION rule_write_guard(
        'source_text', 'value_min', 'value_max', 'unit', 'pdf_page', 'section_ref', 'lga',
        'source_chapter_key', 'quote_status', 'needs_review', 'review_reason', 'is_current',
        'plain_summary');

DROP TRIGGER IF EXISTS zz_rule_write_guard ON regulatory_provisions;
CREATE TRIGGER zz_rule_write_guard BEFORE INSERT OR UPDATE OR DELETE ON regulatory_provisions
    FOR EACH ROW EXECUTE FUNCTION rule_write_guard(
        'provision_text', 'council_quote', 'quote_status', 'quote_page', 'pdf_page',
        'source_council', 'source_chapter_key', 'is_current', 'v2_is_actionable');

DROP TRIGGER IF EXISTS zz_rule_write_guard ON dcp_chapter_registry;
CREATE TRIGGER zz_rule_write_guard BEFORE INSERT OR UPDATE OR DELETE ON dcp_chapter_registry
    FOR EACH ROW EXECUTE FUNCTION rule_write_guard(
        'r2_current_path', 'content_hash', 'page_start', 'page_end', 'needs_extraction',
        'is_active', 'council_url', 'chapter_key');

DROP TRIGGER IF EXISTS zz_rule_write_guard_truncate ON dcp_setback_controls;
CREATE TRIGGER zz_rule_write_guard_truncate BEFORE TRUNCATE ON dcp_setback_controls
    FOR EACH STATEMENT EXECUTE FUNCTION rule_write_guard_truncate();
DROP TRIGGER IF EXISTS zz_rule_write_guard_truncate ON regulatory_provisions;
CREATE TRIGGER zz_rule_write_guard_truncate BEFORE TRUNCATE ON regulatory_provisions
    FOR EACH STATEMENT EXECUTE FUNCTION rule_write_guard_truncate();
DROP TRIGGER IF EXISTS zz_rule_write_guard_truncate ON dcp_chapter_registry;
CREATE TRIGGER zz_rule_write_guard_truncate BEFORE TRUNCATE ON dcp_chapter_registry
    FOR EACH STATEMENT EXECUTE FUNCTION rule_write_guard_truncate();

-- A protected column that does not exist compares NULL to NULL and is never "changed": it
-- would be silently unprotected (renamed or misspelt). Refuse to install in that state.
DO $$
DECLARE
    r record;
BEGIN
    FOR r IN SELECT c.relname AS tbl, m[1] AS col
               FROM pg_trigger t
               JOIN pg_class c ON c.oid = t.tgrelid
               CROSS JOIN LATERAL regexp_matches(pg_get_triggerdef(t.oid),
                                                 $re$'([a-z0-9_]+)'$re$, 'g') AS m
              WHERE t.tgname = 'zz_rule_write_guard'
    LOOP
        IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                        WHERE table_name = r.tbl AND column_name = r.col) THEN
            RAISE EXCEPTION 'rule_write_guard: % has no column % -- it would be unprotected', r.tbl, r.col;
        END IF;
    END LOOP;
END;
$$;
