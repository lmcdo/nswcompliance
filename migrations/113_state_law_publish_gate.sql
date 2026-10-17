-- 113: publish-time gate for state law (DQ-145 step 7, user plan 2026-10-17): no NEW state-law row is served
-- until its citation is proven -- the state-law mirror of the council DQ-101 page-proof gate.
--
-- prior-art-checked: council rows are gated inside the DCP pipeline (scripts/dcp_fidelity_gate.py, DQ-101). State-law
-- rows (source_council IS NULL) have no pipeline: they arrive from one-off scripts (e.g.
-- scripts/extract_from_documents_table.py), so the only place every writer passes through is the table itself.
-- Same trigger style as migrations 079 / 111 / 112.
--
-- 1. REFUSE (raise) an INSERT, or an UPDATE that starts serving a row (v2_is_actionable or is_current turned on),
--    of a state-law row whose citation_status is not 'proven' / 'imprecise'. Rows already served are untouched,
--    so the 2026-10-17 backlog (DQ-145) keeps its "Citation not yet checked" mark and can only shrink.
--    A withheld row comes back only once a proof script has proven it.
-- 2. VOID the proof of a state-law row whose text changes, unless the same write re-checks it (citation_checked_at
--    changes too -- every proof applier sets it). A proven label on words nobody checked is the DQ-111 class.
--
-- Rollback: DROP TRIGGER trg_rp_state_law_b_publish_gate ON regulatory_provisions;
--           DROP TRIGGER trg_rp_state_law_a_void_proof ON regulatory_provisions;
--           DROP FUNCTION regulatory_provisions_state_law_publish_gate(); DROP FUNCTION regulatory_provisions_state_law_void_proof();

CREATE OR REPLACE FUNCTION regulatory_provisions_state_law_void_proof() RETURNS trigger AS $$
BEGIN
    IF NEW.source_council IS NULL
       AND NEW.provision_text IS DISTINCT FROM OLD.provision_text
       AND NEW.citation_checked_at IS NOT DISTINCT FROM OLD.citation_checked_at THEN
        NEW.citation_status := NULL;
        NEW.citation_source_path := NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION regulatory_provisions_state_law_publish_gate() RETURNS trigger AS $$
BEGIN
    IF NEW.source_council IS NULL
       AND COALESCE(NEW.is_current, FALSE) AND COALESCE(NEW.v2_is_actionable, FALSE)
       AND COALESCE(NEW.citation_status, '') NOT IN ('proven', 'imprecise')
       AND (TG_OP = 'INSERT' OR NOT (COALESCE(OLD.is_current, FALSE) AND COALESCE(OLD.v2_is_actionable, FALSE))) THEN
        RAISE EXCEPTION 'state-law row % (%, %) would start being served with citation_status %: prove it first '
                        '(migration 113, DQ-145)', NEW.id, NEW.document_id, NEW.ref_number, NEW.citation_status
              USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 'a' before 'b': BEFORE triggers fire in name order, so a text change voids the proof before the gate looks.
DROP TRIGGER IF EXISTS trg_rp_state_law_a_void_proof ON regulatory_provisions;
CREATE TRIGGER trg_rp_state_law_a_void_proof
    BEFORE UPDATE OF provision_text ON regulatory_provisions
    FOR EACH ROW EXECUTE FUNCTION regulatory_provisions_state_law_void_proof();

DROP TRIGGER IF EXISTS trg_rp_state_law_b_publish_gate ON regulatory_provisions;
CREATE TRIGGER trg_rp_state_law_b_publish_gate
    BEFORE INSERT OR UPDATE ON regulatory_provisions
    FOR EACH ROW EXECUTE FUNCTION regulatory_provisions_state_law_publish_gate();
