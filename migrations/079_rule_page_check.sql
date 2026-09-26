-- 079: does a served DCP rule's page link open the page the rule is on, and what does that page print?
--
-- prior-art-checked: pdf_printed_page (integer) exists but is NULL on every served council DCP row, and
-- councils print page numbers as text ("B5", "14-117", "4.1-2"); nothing records whether pdf_page holds
-- the rule -- citation_status (076) proves the clause NUMBER and uses the page only as a search hint.
--
-- Measured 2026-09-26 over all 237 served chapter PDFs (17,489 rules): 45% of page links opened the
-- first page of the AI reader's 12-page chunk (scripts/ai_extractor.py stored `a + 1` for every rule).
-- scripts/dcp_page_repair.py writes these columns; the site reads them.
--
-- page_check: on_page | moved (link corrected) | unresolved (same wording on several pages, or the
-- two locators disagree -- the link is NOT to be trusted) | not_found | too_short | no_source.
-- NULL = not checked yet.

ALTER TABLE regulatory_provisions
    ADD COLUMN IF NOT EXISTS printed_page_label text,
    ADD COLUMN IF NOT EXISTS page_check text
        CHECK (page_check IN ('on_page', 'moved', 'unresolved', 'not_found', 'too_short', 'no_source')),
    ADD COLUMN IF NOT EXISTS page_checked_at timestamptz,
    ADD COLUMN IF NOT EXISTS page_source_path text;

-- Each chapter PDF's own page numbering, found once from the pages whose footer can be read and
-- applied to all its pages: [{"prefix": "B", "offset": -2, "first": 3, "last": 54, "seen": 50}].
-- printed number = prefix || (PDF page + offset). NULL = not measured for the current PDF.
ALTER TABLE dcp_chapter_registry
    ADD COLUMN IF NOT EXISTS page_numbering jsonb,
    ADD COLUMN IF NOT EXISTS page_numbering_path text;

CREATE INDEX IF NOT EXISTS regulatory_provisions_page_check_idx
    ON regulatory_provisions (page_check) WHERE is_current;

-- A rule whose text or page changes, by anything other than the page check itself, forgets its
-- verdict: an unchecked link is visible to the health check, a stale "on_page" is not.
CREATE OR REPLACE FUNCTION regulatory_provisions_clear_page_check() RETURNS trigger AS $$
BEGIN
    IF (NEW.provision_text IS DISTINCT FROM OLD.provision_text
        OR NEW.pdf_page IS DISTINCT FROM OLD.pdf_page
        OR NEW.source_chapter_key IS DISTINCT FROM OLD.source_chapter_key)
       AND NEW.page_checked_at IS NOT DISTINCT FROM OLD.page_checked_at THEN
        NEW.page_check := NULL;
        NEW.printed_page_label := NULL;
        NEW.page_checked_at := NULL;
        NEW.page_source_path := NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS regulatory_provisions_clear_page_check ON regulatory_provisions;
CREATE TRIGGER regulatory_provisions_clear_page_check
    BEFORE UPDATE ON regulatory_provisions
    FOR EACH ROW EXECUTE FUNCTION regulatory_provisions_clear_page_check();

-- A new PDF for a chapter voids every page verdict judged on the old one (same rule as 078 for citations).
CREATE OR REPLACE FUNCTION dcp_chapter_registry_void_page_checks() RETURNS trigger AS $$
BEGIN
    IF NEW.r2_current_path IS DISTINCT FROM OLD.r2_current_path
       OR NEW.is_active IS DISTINCT FROM OLD.is_active THEN
        UPDATE regulatory_provisions
           SET page_check = NULL, printed_page_label = NULL, page_checked_at = NULL, page_source_path = NULL
         WHERE source_council = NEW.council AND source_chapter_key = NEW.chapter_key
           AND is_current AND page_check IS NOT NULL;
        NEW.page_numbering := NULL;          -- measured on the old PDF
        NEW.page_numbering_path := NULL;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS dcp_chapter_registry_void_page_checks ON dcp_chapter_registry;
CREATE TRIGGER dcp_chapter_registry_void_page_checks
    BEFORE UPDATE OF r2_current_path, is_active ON dcp_chapter_registry
    FOR EACH ROW EXECUTE FUNCTION dcp_chapter_registry_void_page_checks();
