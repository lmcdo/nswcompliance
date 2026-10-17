-- 113: publish-time gate for state law (DQ-145 step 7, user plan 2026-10-17): no NEW state-law text is served
-- until its citation is proven -- the state-law mirror of the council DQ-101 page-proof gate.
--
-- prior-art-checked: council rows are gated inside the DCP pipeline (scripts/dcp_fidelity_gate.py, DQ-101). State-law
-- rows (source_council IS NULL) have no pipeline: they arrive from one-off scripts (e.g.
-- scripts/extract_from_documents_table.py), so the only place every writer passes through is the table itself.
-- Same trigger style as migrations 079 / 111 / 112.
--
-- 1. VOID the proof of a state-law row whose text changes, unless the same statement supplies NEW evidence: both
--    citation_checked_at and citation_source_path change (scripts/revert_row_from_backup.py restoring a proven
--    version). Refreshing the timestamp alone keeps nothing (cross-review 2026-10-17). The appliers write the text,
--    then the proof, in two statements of one transaction. A proven label on unchecked words is DQ-111.
--    A council row turned into state law (source_council set to NULL) also loses its proof: it was a council-PDF proof.
-- 2. REFUSE, at COMMIT, a transaction that leaves a served state-law row unproven after it was inserted, had its text
--    changed, started being served, or became state law (source_council set to NULL). The check is DEFERRED and
--    re-reads the row, so the proof appliers -- which write the text and then the proof in one transaction
--    (scripts/apply_sepp_marker_blind.py) -- still pass. Cross-review 2026-10-17: a flag-transition-only BEFORE trigger
--    missed a text change on an already-served row and a council row turned into state law.
--    Untouched rows are not checked: the 2026-10-17 backlog (DQ-145) keeps its "Citation not yet checked" mark and
--    can only shrink. A proof status lowered by a checker (e.g. to 'partial') is not refused either: that is honest.
--
-- Rollback: DROP TRIGGER trg_rp_state_law_publish_gate ON regulatory_provisions;
--           DROP TRIGGER trg_rp_state_law_void_proof ON regulatory_provisions;
--           DROP FUNCTION regulatory_provisions_state_law_publish_gate(); DROP FUNCTION regulatory_provisions_state_law_void_proof();

CREATE OR REPLACE FUNCTION regulatory_provisions_state_law_void_proof() RETURNS trigger AS $$
BEGIN
    IF NEW.source_council IS NULL AND (
          (OLD.source_council IS NOT NULL)   -- a council proof (its PDF page) says nothing about state law
       OR (NEW.provision_text IS DISTINCT FROM OLD.provision_text
           AND (NEW.citation_checked_at IS NOT DISTINCT FROM OLD.citation_checked_at
                OR NEW.citation_source_path IS NOT DISTINCT FROM OLD.citation_source_path))) THEN
        NEW.citation_status := NULL;
        NEW.citation_source_path := NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION regulatory_provisions_state_law_publish_gate() RETURNS trigger AS $$
DECLARE
    now_council text;
    now_current boolean;
    now_served boolean;
    now_status text;
BEGIN
    IF TG_OP = 'UPDATE'
       AND NEW.provision_text IS NOT DISTINCT FROM OLD.provision_text
       AND OLD.source_council IS NULL
       AND COALESCE(OLD.is_current, FALSE) AND COALESCE(OLD.v2_is_actionable, FALSE) THEN
        RETURN NULL;   -- an already-served state-law row whose words did not change: not new text
    END IF;
    -- deferred to COMMIT: judge the row as the transaction leaves it, not as this one statement did
    SELECT source_council, is_current, v2_is_actionable, citation_status
      INTO now_council, now_current, now_served, now_status
      FROM regulatory_provisions WHERE id = NEW.id;
    IF FOUND AND now_council IS NULL AND COALESCE(now_current, FALSE) AND COALESCE(now_served, FALSE)
       AND COALESCE(now_status, '') NOT IN ('proven', 'imprecise') THEN
        RAISE EXCEPTION 'state-law row % (%, %) would be served with new, unproven text (citation_status %): '
                        'prove it in the same transaction or withhold it (migration 113, DQ-145)',
                        NEW.id, NEW.document_id, NEW.ref_number, now_status
              USING ERRCODE = 'check_violation';
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_rp_state_law_void_proof ON regulatory_provisions;
CREATE TRIGGER trg_rp_state_law_void_proof
    BEFORE UPDATE OF provision_text, source_council ON regulatory_provisions
    FOR EACH ROW EXECUTE FUNCTION regulatory_provisions_state_law_void_proof();

DROP TRIGGER IF EXISTS trg_rp_state_law_publish_gate ON regulatory_provisions;
CREATE CONSTRAINT TRIGGER trg_rp_state_law_publish_gate
    AFTER INSERT OR UPDATE OF provision_text, is_current, v2_is_actionable, source_council ON regulatory_provisions
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION regulatory_provisions_state_law_publish_gate();
