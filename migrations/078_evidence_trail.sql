-- 078: every shown citation and every report can be traced to the exact source it was checked against.
--
-- prior-art-checked: report_audit_trail (append-only by convention only, SHA-256 per data source,
-- written by services/audit_trail.py) and migration 077's citation verdicts. Neither records WHICH
-- version of a council PDF a verdict was judged on, nothing chains or protects the audit rows, and
-- the paid conveyancing report writes no audit row at all (measured 2026-09-26: 887 rows, none
-- 'conveyancing').

-- 1. The source version a verdict was judged on (the chapter's r2_current_path at the time).
ALTER TABLE regulatory_provisions  ADD COLUMN IF NOT EXISTS citation_source_path text;
ALTER TABLE dcp_setback_controls   ADD COLUMN IF NOT EXISTS citation_source_path text;

-- 2. A new PDF for a chapter voids every verdict judged on the old one, at once and in the database,
--    so a failed or skipped re-check leaves the clause HIDDEN rather than proven against a
--    superseded plan (cross-review finding on #1173). The writers re-judge on the next run.
CREATE OR REPLACE FUNCTION dcp_chapter_registry_void_citations() RETURNS trigger AS $$
BEGIN
    IF NEW.r2_current_path IS DISTINCT FROM OLD.r2_current_path
       OR NEW.is_active IS DISTINCT FROM OLD.is_active THEN
        UPDATE regulatory_provisions
           SET citation_status = NULL, citation_checked_at = NULL, citation_source_path = NULL
         WHERE source_council = NEW.council AND source_chapter_key = NEW.chapter_key
           AND is_current AND citation_status IS NOT NULL;
        UPDATE dcp_setback_controls
           SET citation_status = NULL, citation_checked_at = NULL, citation_source_path = NULL
         WHERE lga = NEW.council AND source_chapter_key = NEW.chapter_key
           AND is_current AND citation_status IS NOT NULL AND citation_status <> 'external';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS dcp_chapter_registry_void_citations ON dcp_chapter_registry;
CREATE TRIGGER dcp_chapter_registry_void_citations
    AFTER UPDATE OF r2_current_path, is_active ON dcp_chapter_registry
    FOR EACH ROW EXECUTE FUNCTION dcp_chapter_registry_void_citations();

-- 3. report_audit_trail becomes a hash chain: each row's digest covers its content and the previous
--    row's digest, so any later edit, deletion or insertion breaks every digest after it.
--    scripts/verify_audit_chain.py recomputes the chain.
ALTER TABLE report_audit_trail ADD COLUMN IF NOT EXISTS chain_seq bigint;
ALTER TABLE report_audit_trail ADD COLUMN IF NOT EXISTS prev_hash text;
ALTER TABLE report_audit_trail ADD COLUMN IF NOT EXISTS row_hash text;
CREATE SEQUENCE IF NOT EXISTS report_audit_trail_chain_seq;

-- The ONE definition of a row's digest, used by the insert trigger and by the verifier.
CREATE OR REPLACE FUNCTION report_audit_trail_digest(r report_audit_trail, prev text) RETURNS text AS $$
    SELECT encode(sha256(convert_to(coalesce(prev, '') || jsonb_build_object(
        'id', r.id, 'report_id', r.report_id, 'pipeline_name', r.pipeline_name,
        'pipeline_version', r.pipeline_version, 'input_params', r.input_params,
        'data_sources_queried', r.data_sources_queried,
        'intermediate_calculations', r.intermediate_calculations,
        'output_summary', r.output_summary, 'disclaimer_version', r.disclaimer_version,
        'created_at', to_char(r.created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US'),
        'chain_seq', r.chain_seq)::text, 'UTF8')), 'hex')
$$ LANGUAGE sql IMMUTABLE;

-- Chain the existing rows in created_at order (once; rows already chained are skipped).
DO $$
DECLARE rec report_audit_trail; prev text;
BEGIN
    SELECT row_hash INTO prev FROM report_audit_trail WHERE chain_seq IS NOT NULL
     ORDER BY chain_seq DESC LIMIT 1;
    FOR rec IN SELECT * FROM report_audit_trail WHERE chain_seq IS NULL ORDER BY created_at, id LOOP
        rec.chain_seq := nextval('report_audit_trail_chain_seq');
        rec.prev_hash := prev;
        rec.row_hash := report_audit_trail_digest(rec, prev);
        UPDATE report_audit_trail
           SET chain_seq = rec.chain_seq, prev_hash = rec.prev_hash, row_hash = rec.row_hash
         WHERE id = rec.id;
        prev := rec.row_hash;
    END LOOP;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS report_audit_trail_chain_seq_idx ON report_audit_trail (chain_seq);

-- New rows are chained on insert. The advisory lock serialises concurrent inserts so two
-- reports can never both link to the same previous row.
CREATE OR REPLACE FUNCTION report_audit_trail_chain() RETURNS trigger AS $$
BEGIN
    PERFORM pg_advisory_xact_lock(hashtext('report_audit_trail_chain'));
    NEW.chain_seq := nextval('report_audit_trail_chain_seq');
    SELECT row_hash INTO NEW.prev_hash FROM report_audit_trail ORDER BY chain_seq DESC LIMIT 1;
    NEW.row_hash := report_audit_trail_digest(NEW, NEW.prev_hash);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS report_audit_trail_chain ON report_audit_trail;
CREATE TRIGGER report_audit_trail_chain BEFORE INSERT ON report_audit_trail
    FOR EACH ROW EXECUTE FUNCTION report_audit_trail_chain();

-- Append-only, enforced rather than documented.
CREATE OR REPLACE FUNCTION report_audit_trail_append_only() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'report_audit_trail is append-only (% refused)', TG_OP;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS report_audit_trail_append_only ON report_audit_trail;
CREATE TRIGGER report_audit_trail_append_only BEFORE UPDATE OR DELETE ON report_audit_trail
    FOR EACH ROW EXECUTE FUNCTION report_audit_trail_append_only();

CREATE OR REPLACE FUNCTION report_audit_trail_no_truncate() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'report_audit_trail is append-only (TRUNCATE refused)';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS report_audit_trail_no_truncate ON report_audit_trail;
CREATE TRIGGER report_audit_trail_no_truncate BEFORE TRUNCATE ON report_audit_trail
    FOR EACH STATEMENT EXECUTE FUNCTION report_audit_trail_no_truncate();
