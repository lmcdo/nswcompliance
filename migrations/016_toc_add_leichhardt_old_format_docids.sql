-- Migration 016: Fix NULL page_end on Leichhardt TOC entries + add old-format provision doc_id rows
--
-- TWO PROBLEMS addressed here:
--
-- Problem 1 (NULL page_end):
--   Every chapter's last TOC section has page_end = NULL because the TOC extractor
--   couldn't determine the end boundary (no "next section" to infer it from).
--   BETWEEN x AND NULL is always false → JOIN fails for all provisions on those pages.
--   Fix: set page_end = max(pdf_page) of provisions in that chapter.
--
-- Problem 2 (doc_id format mismatch):
--   86% of Leichhardt provisions have old-format document_ids with spaces/hyphens
--     e.g. 'Leichhardt DCP 2013 - 5 -  Part C Place Section 1 - with IWLEP 2022 amendments March 23'
--   Migration 015 updated dcp_table_of_contents to new slug format
--     e.g. 'Leichhardt_DCP_2013__part_c_s1_general'
--   enrichWithTocSections fuzzy JOIN normalises underscores/hyphens but not spaces,
--   so old-format provision doc_ids never match → toc_section_number = NULL.
--   Fix: INSERT duplicate TOC rows for each old-format provision document_id,
--   copying all section/page data from the now-corrected new-format entry.
--   Purely additive — no existing data modified by the INSERT step.
--
-- Rollback:
--   Part 1 (NULL fix): No rollback available — original NULL values should not be restored.
--   Part 2 (old-format rows): DELETE FROM dcp_table_of_contents WHERE document_id LIKE 'Leichhardt DCP 2013%';

BEGIN;

-- ============================================================
-- PART 1: Fix NULL page_end on new-format TOC last sections
-- ============================================================

-- Part A: last section covers to end of PDF
-- Provisions max page = 9
UPDATE dcp_table_of_contents
SET page_end = (
    SELECT max(pdf_page)
    FROM regulatory_provisions
    WHERE document_id = 'Leichhardt DCP 2013 - 3 - Part A  Introduction - with IWLEP 2022 amendments'
        AND is_current = TRUE
)
WHERE document_id = 'Leichhardt_DCP_2013__part_a_introduction'
    AND page_end IS NULL;

-- Part B: no old-format provisions exist (separate extraction batch), use TOC page range
-- page_start = 6; set page_end = 20 (safe upper bound from PDF page count)
UPDATE dcp_table_of_contents
SET page_end = 20
WHERE document_id = 'Leichhardt_DCP_2013__part_b_connections'
    AND page_end IS NULL;

-- Part C Section 1: last section C1.10 starts at page 48, covers to end of PDF
-- Provisions max page = 109
UPDATE dcp_table_of_contents
SET page_end = (
    SELECT max(pdf_page)
    FROM regulatory_provisions
    WHERE document_id = 'Leichhardt DCP 2013 - 5 -  Part C Place Section 1 - with IWLEP 2022 amendments March 23'
        AND is_current = TRUE
)
WHERE document_id = 'Leichhardt_DCP_2013__part_c_s1_general'
    AND page_end IS NULL;

-- Part D: only 1 TOC row (SECTION 2, starts page 6); provisions cover pages 3-15
-- Provisions max page = 15
UPDATE dcp_table_of_contents
SET page_end = (
    SELECT max(pdf_page)
    FROM regulatory_provisions
    WHERE document_id = 'Leichhardt DCP 2013 - 9 - Part D Energy - with IWLEP 2022 amendments'
        AND is_current = TRUE
)
WHERE document_id = 'Leichhardt_DCP_2013__part_d_energy'
    AND page_end IS NULL;

-- Part E: last section E1.1.5 starts page 6; provisions cover pages 2-20
-- Provisions max page = 20
UPDATE dcp_table_of_contents
SET page_end = (
    SELECT max(pdf_page)
    FROM regulatory_provisions
    WHERE document_id = 'Leichhardt DCP 2013 - 10 - Part E Water - with IWLEP 2022 amendments'
        AND is_current = TRUE
)
WHERE document_id = 'Leichhardt_DCP_2013__part_e_water'
    AND page_end IS NULL;

-- Part F: only 1 TOC row (SECTION 1, starts page 3); provisions cover pages 2-6
-- Provisions max page = 6
UPDATE dcp_table_of_contents
SET page_end = (
    SELECT max(pdf_page)
    FROM regulatory_provisions
    WHERE document_id = 'Leichhardt DCP 2013 - 11 - Part F Food - with IWLEP 2022 amendments'
        AND is_current = TRUE
)
WHERE document_id = 'Leichhardt_DCP_2013__part_f_food'
    AND page_end IS NULL;

-- Part G: last section G12.14 starts page 149; provisions max page ~149
UPDATE dcp_table_of_contents
SET page_end = (
    SELECT max(pdf_page)
    FROM regulatory_provisions
    WHERE document_id = 'Leichhardt DCP 2013 - 12 - Part G Section 1-12 - Amdt 19 - Nov 2023'
        AND is_current = TRUE
)
WHERE document_id = 'Leichhardt_DCP_2013__part_g_s1_site_specific'
    AND page_end IS NULL;

-- ============================================================
-- PART 2: INSERT old-format doc_id duplicate TOC rows
-- ============================================================

-- Part A
INSERT INTO dcp_table_of_contents
  (document_id, section_number, section_title, page_start, page_end, part_number, depth, parent_section)
SELECT
  'Leichhardt DCP 2013 - 3 - Part A  Introduction - with IWLEP 2022 amendments',
  section_number, section_title, page_start, page_end, part_number, depth, parent_section
FROM dcp_table_of_contents
WHERE document_id = 'Leichhardt_DCP_2013__part_a_introduction'
ON CONFLICT DO NOTHING;

-- Part B
INSERT INTO dcp_table_of_contents
  (document_id, section_number, section_title, page_start, page_end, part_number, depth, parent_section)
SELECT
  'Leichhardt DCP 2013 - 4 - Part B Connections - with IWLEP 2022 amendments',
  section_number, section_title, page_start, page_end, part_number, depth, parent_section
FROM dcp_table_of_contents
WHERE document_id = 'Leichhardt_DCP_2013__part_b_connections'
ON CONFLICT DO NOTHING;

-- Part C Section 1 (largest chapter — 590 provisions)
INSERT INTO dcp_table_of_contents
  (document_id, section_number, section_title, page_start, page_end, part_number, depth, parent_section)
SELECT
  'Leichhardt DCP 2013 - 5 -  Part C Place Section 1 - with IWLEP 2022 amendments March 23',
  section_number, section_title, page_start, page_end, part_number, depth, parent_section
FROM dcp_table_of_contents
WHERE document_id = 'Leichhardt_DCP_2013__part_c_s1_general'
ON CONFLICT DO NOTHING;

-- Part D Energy
INSERT INTO dcp_table_of_contents
  (document_id, section_number, section_title, page_start, page_end, part_number, depth, parent_section)
SELECT
  'Leichhardt DCP 2013 - 9 - Part D Energy - with IWLEP 2022 amendments',
  section_number, section_title, page_start, page_end, part_number, depth, parent_section
FROM dcp_table_of_contents
WHERE document_id = 'Leichhardt_DCP_2013__part_d_energy'
ON CONFLICT DO NOTHING;

-- Part E Water
INSERT INTO dcp_table_of_contents
  (document_id, section_number, section_title, page_start, page_end, part_number, depth, parent_section)
SELECT
  'Leichhardt DCP 2013 - 10 - Part E Water - with IWLEP 2022 amendments',
  section_number, section_title, page_start, page_end, part_number, depth, parent_section
FROM dcp_table_of_contents
WHERE document_id = 'Leichhardt_DCP_2013__part_e_water'
ON CONFLICT DO NOTHING;

-- Part F Food
INSERT INTO dcp_table_of_contents
  (document_id, section_number, section_title, page_start, page_end, part_number, depth, parent_section)
SELECT
  'Leichhardt DCP 2013 - 11 - Part F Food - with IWLEP 2022 amendments',
  section_number, section_title, page_start, page_end, part_number, depth, parent_section
FROM dcp_table_of_contents
WHERE document_id = 'Leichhardt_DCP_2013__part_f_food'
ON CONFLICT DO NOTHING;

-- Part G Section 1-12 (505 provisions across 3 PDFs, all map to same new-format slug)
INSERT INTO dcp_table_of_contents
  (document_id, section_number, section_title, page_start, page_end, part_number, depth, parent_section)
SELECT
  'Leichhardt DCP 2013 - 12 - Part G Section 1-12 - Amdt 19 - Nov 2023',
  section_number, section_title, page_start, page_end, part_number, depth, parent_section
FROM dcp_table_of_contents
WHERE document_id = 'Leichhardt_DCP_2013__part_g_s1_site_specific'
ON CONFLICT DO NOTHING;

-- ============================================================
-- Verify counts
-- ============================================================
-- SELECT document_id, count(*) FROM dcp_table_of_contents
-- WHERE document_id LIKE 'Leichhardt DCP 2013%'
-- GROUP BY document_id ORDER BY count(*) DESC;
--
-- After this migration, re-run TOC JOIN rate query:
-- SELECT count(*) as total, count(t.section_number) as joined
-- FROM regulatory_provisions p
-- LEFT JOIN dcp_table_of_contents t
--   ON p.document_id = t.document_id AND p.pdf_page BETWEEN t.page_start AND t.page_end
-- WHERE p.document_id LIKE 'Leichhardt%' AND p.is_current = TRUE;
-- Target: >80% joined (up from 14%)

COMMIT;
