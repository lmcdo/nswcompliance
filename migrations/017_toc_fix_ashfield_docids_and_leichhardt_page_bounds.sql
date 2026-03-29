-- Migration 017: Fix Ashfield TOC document_id mismatches + Leichhardt page boundary gaps
--
-- ASHFIELD (0% join rate → ~93% after fix):
--   5 chapters have space-format document_ids (e.g. 'Inner West Ashfield DCP 2016 - Chapter A - Miscellaneous')
--   Provisions use underscore format (e.g. 'Inner_West_Ashfield_DCP_2016__chapter_a_miscellaneous')
--   Fix: UPDATE document_id on 5 space-format chapters + rename Chapter D to match provision format.
--   Note: chapter_e2_haberfield (121 provisions) has no TOC at all — needs separate extraction.
--
-- LEICHHARDT (67.6% → ~98% after fix):
--   Several chapters have provisions outside their TOC page ranges:
--   - part_b_connections: page_end=20 but provisions exist at pages 21, 22
--   - part_c_s1_general: page_start=3 but provisions exist at pages 1, 2
--   - part_d_energy: page_start=6 but provisions exist at pages 2-5
--   - part_e_water: page_start=4 but provisions exist at pages 2, 3
--   - part_f_food: page_start=3 but provisions exist at page 2
--   - part_c_s2/s3/s4: TOC uses absolute page numbers (304+, 341+, 375+) from compiled PDF
--     but provisions use relative page numbers (1-based). Add catch-all entries (page 1, no upper bound).
--   - part_g_s13: same absolute page number issue (150+). Add catch-all.
--
-- Also fixes Chapter F (page_start=4 but provision at page 3) and Chapter E1 (page_start=5 but provisions at page 3).
--
-- Rollback:
--   Ashfield: UPDATE document_id back to space-format values.
--   Leichhardt page fixes: revert page_start/page_end values (see comments).
--   Catch-all rows: DELETE FROM dcp_table_of_contents WHERE section_number IN ('C2','C3','C4','G13') AND depth = 0;

BEGIN;

-- ============================================================
-- ASHFIELD: Rename space-format document_ids to match provisions
-- ============================================================

UPDATE dcp_table_of_contents
SET document_id = 'Inner_West_Ashfield_DCP_2016__chapter_a_miscellaneous'
WHERE document_id = 'Inner West Ashfield DCP 2016 - Chapter A - Miscellaneous';

UPDATE dcp_table_of_contents
SET document_id = 'Inner_West_Ashfield_DCP_2016__chapter_b_public_domain'
WHERE document_id = 'Inner West Ashfield DCP 2016 - Chapter B - Public Domain';

UPDATE dcp_table_of_contents
SET document_id = 'Inner_West_Ashfield_DCP_2016__chapter_c_sustainability'
WHERE document_id = 'Inner West Ashfield DCP 2016 - Chapter C - Sustainability';

UPDATE dcp_table_of_contents
SET document_id = 'Inner_West_Ashfield_DCP_2016__chapter_e1_heritage'
WHERE document_id = 'Inner West Ashfield DCP 2016 - Chapter E1 - Heritage';

UPDATE dcp_table_of_contents
SET document_id = 'Inner_West_Ashfield_DCP_2016__chapter_f_dev_category'
WHERE document_id = 'Inner West Ashfield DCP 2016 - Chapter F - Development Category';

-- Chapter D: triple-underscore / mixed-case name → lowercase slug
UPDATE dcp_table_of_contents
SET document_id = 'Inner_West_Ashfield_DCP_2016__chapter_d_precinct_guidelines'
WHERE document_id = 'Inner_West_Ashfield_DCP_2016___Chapter_D___Precinct_Guidelines_with_IWLEP_2022_amendments_Nov_22';

-- ============================================================
-- ASHFIELD: Extend page boundaries to cover pre-chapter intro provisions
-- ============================================================

-- Chapter F: provisions start at page 3, first TOC entry starts at page 4
-- Extend page_start from 4 to 1 (was 4)
UPDATE dcp_table_of_contents
SET page_start = 1
WHERE document_id = 'Inner_West_Ashfield_DCP_2016__chapter_f_dev_category'
  AND page_start = 4;

-- Chapter E1: all 231 provisions are on page 3, first TOC entry starts at page 5
-- Extend page_start from 5 to 1
UPDATE dcp_table_of_contents
SET page_start = 1
WHERE document_id = 'Inner_West_Ashfield_DCP_2016__chapter_e1_heritage'
  AND page_start = 5;

-- ============================================================
-- LEICHHARDT: Fix page boundary gaps on existing entries
-- ============================================================

-- part_b_connections: provisions at pages 21, 22 fall after page_end=20
-- Extend last entry to have no upper bound
UPDATE dcp_table_of_contents
SET page_end = NULL
WHERE document_id = 'Leichhardt_DCP_2013__part_b_connections'
  AND page_end = 20;

-- Also fix space-format duplicate (inserted by migration 016)
UPDATE dcp_table_of_contents
SET page_end = NULL
WHERE document_id = 'Leichhardt DCP 2013 - 4 - Part B Connections - with IWLEP 2022 amendments'
  AND page_end = 20;

-- part_c_s1_general: provisions at pages 1, 2 fall before page_start=3
-- Extend first entry from page_start=3 to page_start=1
UPDATE dcp_table_of_contents
SET page_start = 1
WHERE document_id = 'Leichhardt_DCP_2013__part_c_s1_general'
  AND page_start = 3
  AND page_end = 4;

-- Also fix space-format duplicate
UPDATE dcp_table_of_contents
SET page_start = 1
WHERE document_id = 'Leichhardt DCP 2013 - 5 -  Part C Place Section 1 - with IWLEP 2022 amendments March 23'
  AND page_start = 3
  AND page_end = 4;

-- part_d_energy: provisions at pages 2-5 fall before page_start=6
-- Extend from page_start=6 to page_start=1
UPDATE dcp_table_of_contents
SET page_start = 1
WHERE document_id = 'Leichhardt_DCP_2013__part_d_energy'
  AND page_start = 6;

-- Also fix space-format duplicate
UPDATE dcp_table_of_contents
SET page_start = 1
WHERE document_id = 'Leichhardt DCP 2013 - 9 - Part D Energy - with IWLEP 2022 amendments'
  AND page_start = 6;

-- part_e_water: provisions at pages 2, 3 fall before page_start=4
UPDATE dcp_table_of_contents
SET page_start = 1
WHERE document_id = 'Leichhardt_DCP_2013__part_e_water'
  AND page_start = 4;

-- Also fix space-format duplicate
UPDATE dcp_table_of_contents
SET page_start = 1
WHERE document_id = 'Leichhardt DCP 2013 - 10 - Part E Water - with IWLEP 2022 amendments'
  AND page_start = 4;

-- part_f_food: provisions at page 2 fall before page_start=3
UPDATE dcp_table_of_contents
SET page_start = 1
WHERE document_id = 'Leichhardt_DCP_2013__part_f_food'
  AND page_start = 3;

-- Also fix space-format duplicate
UPDATE dcp_table_of_contents
SET page_start = 1
WHERE document_id = 'Leichhardt DCP 2013 - 11 - Part F Food - with IWLEP 2022 amendments'
  AND page_start = 3;

-- ============================================================
-- LEICHHARDT: Add catch-all entries for chapters with absolute TOC page numbers
--
-- part_c_s2, s3, s4, g_s13 have TOC page_start values in the 150-375 range
-- (absolute pages from a compiled PDF) but provisions use relative pages (1-based).
-- Adding a depth=0 catch-all entry (page 1, no upper bound) ensures provisions
-- in these chapters always find a TOC match. The depth=0 marker allows future
-- cleanup to identify and replace these with proper sub-section entries.
-- ============================================================

-- Part C Section 2: Urban Character
INSERT INTO dcp_table_of_contents
  (document_id, section_number, section_title, page_start, page_end, part_number, depth, parent_section)
VALUES
  ('Leichhardt_DCP_2013__part_c_s2_urban_character', 'C2', 'Urban Character', 1, NULL, 3, 0, NULL);

-- Part C Section 3: Residential
INSERT INTO dcp_table_of_contents
  (document_id, section_number, section_title, page_start, page_end, part_number, depth, parent_section)
VALUES
  ('Leichhardt_DCP_2013__part_c_s3_residential', 'C3', 'Residential', 1, NULL, 3, 0, NULL);

-- Part C Section 4: Non-Residential
INSERT INTO dcp_table_of_contents
  (document_id, section_number, section_title, page_start, page_end, part_number, depth, parent_section)
VALUES
  ('Leichhardt_DCP_2013__part_c_s4_non_residential', 'C4', 'Non-Residential', 1, NULL, 3, 0, NULL);

-- Part G Section 13: Pyrmont Bridge Road
INSERT INTO dcp_table_of_contents
  (document_id, section_number, section_title, page_start, page_end, part_number, depth, parent_section)
VALUES
  ('Leichhardt_DCP_2013__part_g_s13_pyrmont_bridge_rd', 'G13', 'Pyrmont Bridge Road', 1, NULL, 7, 0, NULL);

-- ============================================================
-- Verify: run these after applying to confirm expected rates
-- ============================================================
-- Leichhardt join rate (target ≥85%):
-- SELECT count(*) as total, count(t.section_number) as joined,
--   round(100.0 * count(t.section_number) / count(*), 1) as join_pct
-- FROM regulatory_provisions p
-- LEFT JOIN dcp_table_of_contents t
--   ON p.document_id = t.document_id
--   AND p.pdf_page >= t.page_start
--   AND (t.page_end IS NULL OR p.pdf_page <= t.page_end)
-- WHERE p.is_current = true AND p.source_council = 'leichhardt';
--
-- Ashfield join rate (target ≥80% given chapter_e2 has no TOC):
-- Same query but source_council = 'ashfield'

COMMIT;
