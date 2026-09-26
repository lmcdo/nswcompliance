-- 076: regulatory_provisions.citation_status -- is the served clause number printed on the council's page?
--
-- prior-art-checked: no citation column exists on regulatory_provisions (information_schema, 2026-09-26);
-- the proof itself is scripts/citation_proof.py (DQ-111), which until now only reported.
--
-- DQ-111 found thousands of served DCP rules whose clause number is not proven on the council's page
-- (an AI extraction guess, never checked). Until each is fixed, the site must not show an unproven number
-- as if it were the council's: the serving layer shows the page instead. This column carries the verdict
-- the serving layer reads; scripts/dcp_citation_status.py writes it after every publish and nightly.
--
-- NULL = not checked yet (served as before). Only 'proven' shows the clause number once the UI reads it.

ALTER TABLE regulatory_provisions
    ADD COLUMN IF NOT EXISTS citation_status text
        CHECK (citation_status IN ('proven', 'imprecise', 'not_proven', 'unjudged', 'text_not_found', 'no_source')),
    ADD COLUMN IF NOT EXISTS citation_checked_at timestamptz;

CREATE INDEX IF NOT EXISTS regulatory_provisions_citation_status_idx
    ON regulatory_provisions (citation_status) WHERE is_current;
