-- Migration 018: Fix Marrickville TOC page_start gaps + add Ashfield e2_haberfield TOC entry
--
-- Marrickville: 40 provisions are on pages below their chapter's first TOC entry page_start.
-- All are introductory provisions on page 1 (or pages 1-8 for complex precincts). Fix: extend
-- the minimum page_start to 1 for each affected document_id.
--
-- Ashfield: chapter_e2_haberfield has 121 provisions (all on pdf_page=2) with zero TOC entries.
-- Fix: insert a catch-all entry so the JOIN works. TOC data for this chapter does not exist in
-- extracted form yet — this is a catch-all until a proper TOC extraction is done.
-- TODO: extract actual section-level TOC for chapter_e2_haberfield and replace this catch-all
--       — open item in .claude/DATA_QUALITY_TRACKER.md under ashfield.

-- ── Ashfield e2_haberfield ────────────────────────────────────────────────────────────────────
INSERT INTO dcp_table_of_contents (document_id, section_number, section_title, page_start, page_end, depth, part_number)
VALUES (
    'Inner_West_Ashfield_DCP_2016__chapter_e2_haberfield',
    'E2',
    'Haberfield Neighbourhood (catch-all)',
    1,
    NULL,
    0,
    NULL
);

-- ── Marrickville Part 2 sections ─────────────────────────────────────────────────────────────
-- These sections each have a single TOC entry starting at page 2 or 3, but provisions exist at page 1.

UPDATE dcp_table_of_contents SET page_start = 1
WHERE document_id = 'Marrickville_DCP_2011__part2_s03_site_context_analysis'
  AND page_start = 2;

UPDATE dcp_table_of_contents SET page_start = 1
WHERE document_id = 'Marrickville_DCP_2011__part2_s08_social_impact'
  AND page_start = 2;

UPDATE dcp_table_of_contents SET page_start = 1
WHERE document_id = 'Marrickville_DCP_2011__part2_s09_community_safety'
  AND page_start = 2;

UPDATE dcp_table_of_contents SET page_start = 1
WHERE document_id = 'Marrickville_DCP_2011__part2_s13_biodiversity'
  AND page_start = 2;

UPDATE dcp_table_of_contents SET page_start = 1
WHERE document_id = 'Marrickville_DCP_2011__part2_s14_unique_env_features'
  AND page_start = 2;

UPDATE dcp_table_of_contents SET page_start = 1
WHERE document_id = 'Marrickville_DCP_2011__part2_s17_water_sensitive'
  AND page_start = 3;

-- part2_s18_landscaping: single entry starting at page 11; provisions at pages 1 and 6.
UPDATE dcp_table_of_contents SET page_start = 1
WHERE document_id = 'Marrickville_DCP_2011__part2_s18_landscaping'
  AND page_start = 11;

-- ── Marrickville Part 3-8 ────────────────────────────────────────────────────────────────────

UPDATE dcp_table_of_contents SET page_start = 1
WHERE document_id = 'Marrickville_DCP_2011__part3_subdivision'
  AND page_start = 3;

UPDATE dcp_table_of_contents SET page_start = 1
WHERE document_id = 'Marrickville_DCP_2011__part4_s2_multi_dwelling'
  AND page_start = 2;

UPDATE dcp_table_of_contents SET page_start = 1
WHERE document_id = 'Marrickville_DCP_2011__part7_s1_childcare'
  AND page_start = 2;

UPDATE dcp_table_of_contents SET page_start = 1
WHERE document_id = 'Marrickville_DCP_2011__part7_s3_sex_industry'
  AND page_start = 3;

-- part8_heritage: first TOC entry is 8.1 Introduction at page 15; provision at page 1 is intro text.
-- Only update section 8.1 (not 8.1.2+ which also start at 15).
UPDATE dcp_table_of_contents SET page_start = 1
WHERE document_id = 'Marrickville_DCP_2011__part8_heritage'
  AND section_number = '8.1';

-- ── Marrickville Part 9 precincts ────────────────────────────────────────────────────────────
-- Each precinct has provisions at page 1 (and sometimes lower pages) not covered by TOC entries.

UPDATE dcp_table_of_contents SET page_start = 1
WHERE document_id = 'Marrickville_DCP_2011__part9_p01_lewisham_north'
  AND page_start = 2;

UPDATE dcp_table_of_contents SET page_start = 1
WHERE document_id = 'Marrickville_DCP_2011__part9_p02_petersham_north'
  AND page_start = 2;

UPDATE dcp_table_of_contents SET page_start = 1
WHERE document_id = 'Marrickville_DCP_2011__part9_p03_stanmore_north'
  AND page_start = 2;

UPDATE dcp_table_of_contents SET page_start = 1
WHERE document_id = 'Marrickville_DCP_2011__part9_p06_petersham_south'
  AND page_start = 2;

UPDATE dcp_table_of_contents SET page_start = 1
WHERE document_id = 'Marrickville_DCP_2011__part9_p09_newington'
  AND page_start = 2;

UPDATE dcp_table_of_contents SET page_start = 1
WHERE document_id = 'Marrickville_DCP_2011__part9_p15_enmore_park'
  AND page_start = 3;

UPDATE dcp_table_of_contents SET page_start = 1
WHERE document_id = 'Marrickville_DCP_2011__part9_p20_marrickville_tc_north'
  AND page_start = 2;

UPDATE dcp_table_of_contents SET page_start = 1
WHERE document_id = 'Marrickville_DCP_2011__part9_p21_ness_park'
  AND page_start = 2;

UPDATE dcp_table_of_contents SET page_start = 1
WHERE document_id = 'Marrickville_DCP_2011__part9_p22_dulwich_hill_stn_south'
  AND page_start = 2;

-- p25: single entry starting at page 9; provisions at pages 1, 5, 6, 8.
UPDATE dcp_table_of_contents SET page_start = 1
WHERE document_id = 'Marrickville_DCP_2011__part9_p25_st_peters_triangle'
  AND page_start = 9;

UPDATE dcp_table_of_contents SET page_start = 1
WHERE document_id = 'Marrickville_DCP_2011__part9_p26_barwon_park'
  AND page_start = 2;

-- p32: single entry starting at page 9; provisions at pages 1, 5, 6, 8.
UPDATE dcp_table_of_contents SET page_start = 1
WHERE document_id = 'Marrickville_DCP_2011__part9_p32_cooks_river_east'
  AND page_start = 9;

UPDATE dcp_table_of_contents SET page_start = 1
WHERE document_id = 'Marrickville_DCP_2011__part9_p35_parramatta_rd'
  AND page_start = 3;

-- p36: single entry starting at page 8; provisions at pages 1, 5, 6.
UPDATE dcp_table_of_contents SET page_start = 1
WHERE document_id = 'Marrickville_DCP_2011__part9_p36_petersham_commercial'
  AND page_start = 8;

-- p38: entries starting at pages 8 and 9; provisions at pages 1, 5, 6.
UPDATE dcp_table_of_contents SET page_start = 1
WHERE document_id = 'Marrickville_DCP_2011__part9_p38_dulwich_hill_commercial'
  AND page_start = 8;

-- p47: single entry starting at page 12; provisions at pages 1 and 4.
UPDATE dcp_table_of_contents SET page_start = 1
WHERE document_id = 'Marrickville_DCP_2011__part9_p47_victoria_road'
  AND page_start = 12;
