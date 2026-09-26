-- 077: a label is proven only when every piece of it was checked; setback controls get the same verdict.
--
-- prior-art-checked: extends migration 076 (regulatory_provisions.citation_status). No citation
-- column exists on dcp_setback_controls (information_schema, 2026-09-26).
--
-- 1. 'partial' on regulatory_provisions: the page proves some pieces of the label ("C2.2.4.1 ... C5")
--    but others were never checked ("(a)"). Measured 2026-09-26: 2,713 of 13,950 shown labels.
-- 2. dcp_setback_controls.citation_status: the conveyancing PDF, the Brief, the controls card and the
--    parking API all print section_ref. 954 of its current rows are not linked to a checked rule, so
--    076 cannot cover them. 'external' = a state instrument (ADG, Codes SEPP, LEP), outside this check.
--    Written by scripts/dcp_setback_citation_status.py. NULL = not checked: the clause is NOT shown.

ALTER TABLE regulatory_provisions DROP CONSTRAINT IF EXISTS regulatory_provisions_citation_status_check;
ALTER TABLE regulatory_provisions ADD CONSTRAINT regulatory_provisions_citation_status_check
    CHECK (citation_status IN ('proven', 'imprecise', 'partial', 'not_proven', 'unjudged',
                               'text_not_found', 'no_source'));

ALTER TABLE dcp_setback_controls
    ADD COLUMN IF NOT EXISTS citation_status text
        CHECK (citation_status IN ('proven', 'imprecise', 'partial', 'not_proven', 'unjudged',
                                   'text_not_found', 'no_source', 'external')),
    ADD COLUMN IF NOT EXISTS citation_checked_at timestamptz;

-- A verdict belongs to the label, text and page it was judged on. Every path that edits a setback
-- control (the setback-review fix route, repair scripts, re-extraction) would otherwise leave an old
-- 'proven' on a new label. Any change to those fields clears the verdict, so the clause is hidden
-- until scripts/dcp_setback_citation_status.py judges it again (fail closed). lga is included:
-- it decides 'external' and which council's PDF is the proof.
CREATE OR REPLACE FUNCTION dcp_setback_controls_clear_citation_status() RETURNS trigger AS $$
BEGIN
    IF NEW.lga IS DISTINCT FROM OLD.lga
       OR NEW.section_ref IS DISTINCT FROM OLD.section_ref
       OR NEW.source_text IS DISTINCT FROM OLD.source_text
       OR NEW.pdf_page IS DISTINCT FROM OLD.pdf_page
       OR NEW.source_chapter_key IS DISTINCT FROM OLD.source_chapter_key THEN
        NEW.citation_status := NULL;
        NEW.citation_checked_at := NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS dcp_setback_controls_clear_citation_status ON dcp_setback_controls;
CREATE TRIGGER dcp_setback_controls_clear_citation_status
    BEFORE UPDATE OF lga, section_ref, source_text, pdf_page, source_chapter_key ON dcp_setback_controls
    FOR EACH ROW EXECUTE FUNCTION dcp_setback_controls_clear_citation_status();
