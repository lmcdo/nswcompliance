-- 111: the council's own words for each served DCP rule, copied from its PDF by a program.
--
-- prior-art-checked: no column holds the council's printed text. provision_text is the reader's
-- output (measured 2026-10-12: 4,552 of 19,627 served quotes are not printed word for word, some
-- reworded -- NB 130236). page_check (079) says where a rule is; citation_status (076) proves its
-- clause number. Plan: ~/.claude/plans/ce-council-words-PLAN-2026-10-12.md. Writer:
-- scripts/council_quote.py --apply (deterministic string work; no model writes or approves a quote).
--
-- quote_status:
--   exact          the whole stored rule is printed, in order; council_quote is the council's text there
--   recovered      not printed whole; council_quote is the council's text between its printed opening
--                  and closing words, or from its own label ("(b)", "C3") to the next
--   not_a_control  map labels or a figure caption
--   unconfirmed    none of the above; quote_reason says why. council_quote is NULL and no number from
--                  the rule may be shown as the council's or used in a calculation.
-- NULL = not checked against the chapter's current PDF.

ALTER TABLE regulatory_provisions
    ADD COLUMN IF NOT EXISTS council_quote text,
    ADD COLUMN IF NOT EXISTS quote_page integer,
    ADD COLUMN IF NOT EXISTS quote_source_path text,
    ADD COLUMN IF NOT EXISTS quote_status text
        CHECK (quote_status IN ('exact', 'recovered', 'not_a_control', 'unconfirmed')),
    ADD COLUMN IF NOT EXISTS quote_reason text,
    ADD COLUMN IF NOT EXISTS quote_checked_at timestamptz;

-- A quote is only as good as its status: exact/recovered carry text and a page, nothing else does.
ALTER TABLE regulatory_provisions DROP CONSTRAINT IF EXISTS regulatory_provisions_quote_shape;
ALTER TABLE regulatory_provisions ADD CONSTRAINT regulatory_provisions_quote_shape CHECK (
    quote_status IS NULL
    OR (quote_status IN ('exact', 'recovered') AND council_quote IS NOT NULL AND quote_page IS NOT NULL
        AND quote_source_path IS NOT NULL)
    OR (quote_status IN ('not_a_control', 'unconfirmed') AND council_quote IS NULL AND quote_reason IS NOT NULL));

CREATE INDEX IF NOT EXISTS regulatory_provisions_quote_status_idx
    ON regulatory_provisions (quote_status) WHERE is_current;

-- A rule whose text or chapter changes, by anything other than the copier, forgets its quote:
-- NULL is visible to the nightly check, a stale "exact" is not.
CREATE OR REPLACE FUNCTION regulatory_provisions_clear_quote() RETURNS trigger AS $$
BEGIN
    IF (NEW.provision_text IS DISTINCT FROM OLD.provision_text
        OR NEW.source_chapter_key IS DISTINCT FROM OLD.source_chapter_key
        OR NEW.source_council IS DISTINCT FROM OLD.source_council)
       AND NEW.quote_checked_at IS NOT DISTINCT FROM OLD.quote_checked_at THEN
        NEW.council_quote := NULL;
        NEW.quote_page := NULL;
        NEW.quote_source_path := NULL;
        NEW.quote_status := NULL;
        NEW.quote_reason := NULL;
        NEW.quote_checked_at := NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS regulatory_provisions_clear_quote ON regulatory_provisions;
CREATE TRIGGER regulatory_provisions_clear_quote
    BEFORE UPDATE ON regulatory_provisions
    FOR EACH ROW EXECUTE FUNCTION regulatory_provisions_clear_quote();

-- A new PDF for a chapter voids every quote copied from the old one.
CREATE OR REPLACE FUNCTION dcp_chapter_registry_void_quotes() RETURNS trigger AS $$
BEGIN
    IF NEW.r2_current_path IS DISTINCT FROM OLD.r2_current_path
       OR NEW.is_active IS DISTINCT FROM OLD.is_active THEN
        UPDATE regulatory_provisions
           SET council_quote = NULL, quote_page = NULL, quote_source_path = NULL,
               quote_status = NULL, quote_reason = NULL, quote_checked_at = NULL
         WHERE source_council = NEW.council AND source_chapter_key = NEW.chapter_key
           AND is_current AND quote_status IS NOT NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS dcp_chapter_registry_void_quotes ON dcp_chapter_registry;
CREATE TRIGGER dcp_chapter_registry_void_quotes
    AFTER UPDATE OF r2_current_path, is_active ON dcp_chapter_registry
    FOR EACH ROW EXECUTE FUNCTION dcp_chapter_registry_void_quotes();
