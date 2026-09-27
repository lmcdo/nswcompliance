-- 080: a person read the page and recorded where the rule is printed.
--
-- prior-art-checked: page_check (079) holds only what scripts/dcp_page_repair.py's locator can prove.
-- Some rules are printed where the locator cannot prove them -- a table row stored with its column
-- headings (Wollongong E6 Table 1, Canterbury-Bankstown Figure 62), two rows opening with the same
-- words -- so their link opened the document at page 1 although a person had read the page.
--
-- 'read_by_person' is kept by the repair while the rule's text, page and chapter PDF are unchanged.
-- The 079 triggers already clear any verdict when one of those changes, so a person's reading can
-- never outlive the thing they read.

ALTER TABLE regulatory_provisions DROP CONSTRAINT IF EXISTS regulatory_provisions_page_check_check;
ALTER TABLE regulatory_provisions ADD CONSTRAINT regulatory_provisions_page_check_check
    CHECK (page_check IN ('on_page', 'moved', 'read_by_person', 'unresolved', 'not_found', 'too_short', 'no_source'));

-- The three rows read by a person on 2026-09-27 (rendered page checked by eye): Wollongong E6
-- Table 1, the two "Industrial Development" rows (page 5), and Canterbury-Bankstown Figure 62
-- (page 143). Marked only while still on that page, against the chapter's current PDF.
UPDATE regulatory_provisions rp
   SET page_check = 'read_by_person', page_source_path = reg.r2_current_path, page_checked_at = clock_timestamp()
  FROM dcp_chapter_registry reg
 WHERE reg.is_active AND reg.council = rp.source_council AND reg.chapter_key = rp.source_chapter_key
   AND rp.is_current
   AND ((rp.id IN (138794, 138795) AND rp.pdf_page = 5) OR (rp.id = 132068 AND rp.pdf_page = 143));
