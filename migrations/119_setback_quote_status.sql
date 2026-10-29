-- 119: record, per DCP number rule, whether its quote is the council's exact words.
--
-- WHY
-- ---
-- 876 number rules were served; a whole-PDF check on 2026-10-29 found only 235 whose
-- source_text is printed word for word on the cited page (the rest were typed as
-- summaries in May 2026, PRs #350-#365). citation_status cannot carry this: it records
-- whether the CLAUSE NUMBER is printed on the page (scripts/dcp_citation_status.py),
-- not whether the quote is.
--
-- VALUES (written only by scripts/dcp_quote_status.py)
--   verbatim    quote found on pdf_page (or across its page break with a neighbour page)
--   wrong_page  quote found in the chapter PDF, but not on pdf_page
--   not_found   quote not in the chapter PDF at all
--   no_source   no PDF, no page, no quote, or the PDF has no text
--   NULL        never checked
--
-- Migration 120 adds the trigger that keeps any row that is not 'verbatim' out of service.
-- It is separate so the served rows can be stamped between the two; applying both at once
-- would hide every rule.

ALTER TABLE dcp_setback_controls
    ADD COLUMN IF NOT EXISTS quote_status text,
    ADD COLUMN IF NOT EXISTS quote_checked_at timestamptz;

ALTER TABLE dcp_setback_controls
    DROP CONSTRAINT IF EXISTS dcp_setback_controls_quote_status_check;
ALTER TABLE dcp_setback_controls
    ADD CONSTRAINT dcp_setback_controls_quote_status_check
    CHECK (quote_status IS NULL
           OR quote_status IN ('verbatim', 'wrong_page', 'not_found', 'no_source'));
