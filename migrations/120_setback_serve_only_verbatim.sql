-- 120: a DCP number rule is served only when its quote is proven verbatim.
--
-- Every reader of dcp_setback_controls that shows a number already hides needs_review rows
-- (scripts/conveyancing_db.fetch_dcp_setbacks, services/granny_flat.py,
-- services/dcp_controls_api.py, app/api/dcp/structured-controls, app/api/canibuildit/check,
-- app/api/tod/parking-rates, lib/parking-rate-selection.ts). So the gate is enforced here,
-- once, instead of in each reader: a current row that is not 'verbatim' cannot have
-- needs_review = false.
--
-- 1. Changing the quote, the page, the chapter or the source path wipes the proof
--    (quote_status := NULL), unless the same statement writes a new quote_status.
--    A proof is about one quote on one page.
-- 2. Any current row whose quote_status is not 'verbatim' is held: needs_review := true,
--    with the reason in review_reason so the hold is visible in the review queue.
--    Releasing a row (needs_review := false) without a proof is undone the same way.
-- Proving a row does NOT release it; release stays a deliberate step.
-- Sits beside dcp_setback_controls_clear_citation_status (same pattern, other column).
--
-- Apply only after `scripts/dcp_quote_status.py --apply` has stamped the served rows,
-- or every served rule is hidden.

CREATE OR REPLACE FUNCTION dcp_setback_hold_unproven_quote() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND (
           NEW.source_text          IS DISTINCT FROM OLD.source_text
        OR NEW.pdf_page             IS DISTINCT FROM OLD.pdf_page
        OR NEW.source_chapter_key   IS DISTINCT FROM OLD.source_chapter_key
        OR NEW.citation_source_path IS DISTINCT FROM OLD.citation_source_path)
       AND NEW.quote_status IS NOT DISTINCT FROM OLD.quote_status THEN
        NEW.quote_status := NULL;
        NEW.quote_checked_at := NULL;
    END IF;

    IF NEW.is_current
       AND NEW.quote_status IS DISTINCT FROM 'verbatim'
       AND NEW.needs_review IS NOT TRUE THEN
        NEW.needs_review := TRUE;
        NEW.review_reason := 'quote not proven word for word on the cited PDF page ('
                             || COALESCE(NEW.quote_status, 'unchecked') || ')';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS dcp_setback_hold_unproven_quote ON dcp_setback_controls;
CREATE TRIGGER dcp_setback_hold_unproven_quote
    BEFORE INSERT OR UPDATE ON dcp_setback_controls
    FOR EACH ROW EXECUTE FUNCTION dcp_setback_hold_unproven_quote();
