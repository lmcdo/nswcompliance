-- Migration 024: Ashfield chapter_b_public_domain + chapter_e2_haberfield TOC granularity
--
-- Problem: Both chapters had COUNCIL_CHAPTER_RANGES configured as a single page range,
--          causing all provisions to get the same pdf_page (4 and 2 respectively).
--          Even with correct TOC entries, all provisions joined to one section.
--
-- Fix: Expanded COUNCIL_CHAPTER_RANGES to per-section page ranges in dcp_extract_changed.py
--      (commit on fix/ashfield-toc-granularity branch). Re-extracted both chapters.
--      Results: chapter_b 49 -> 55 provisions across 7 pages; e2 121 -> 134 across 17 pages.
--
-- This migration replaces the old TOC entries to match the new page structure.
--
-- chapter_b: Old entries had overlapping page ranges (e.g. page 6 matched sections 2,3,4).
--            Replaced with 7 non-overlapping entries matching COUNCIL_CHAPTER_RANGES.
-- e2:        Catch-all entry (depth=0) replaced with 17 per-section entries.
--            Closes DQ-28.

BEGIN;

-- ── chapter_b_public_domain ──────────────────────────────────────────────────

-- Remove old 10 overlapping sections (numbered '1' through '10')
DELETE FROM dcp_table_of_contents
WHERE document_id = 'Inner_West_Ashfield_DCP_2016__chapter_b_public_domain';

-- Insert 7 non-overlapping sections matching COUNCIL_CHAPTER_RANGES
INSERT INTO dcp_table_of_contents
  (document_id, section_number, section_title, page_start, page_end, depth)
VALUES
  ('Inner_West_Ashfield_DCP_2016__chapter_b_public_domain', 'B-intro',  'Introduction',                          1,  3, 1),
  ('Inner_West_Ashfield_DCP_2016__chapter_b_public_domain', 'B-s1',     'Active Street Frontages',               4,  5, 2),
  ('Inner_West_Ashfield_DCP_2016__chapter_b_public_domain', 'B-s2-3',   'Awnings and Street Trees',              6,  6, 2),
  ('Inner_West_Ashfield_DCP_2016__chapter_b_public_domain', 'B-s4-5',   'Wind Effects and Reflectivity',         7,  7, 2),
  ('Inner_West_Ashfield_DCP_2016__chapter_b_public_domain', 'B-s6-7',   'Public Domain Plan and Footways',       8,  8, 2),
  ('Inner_West_Ashfield_DCP_2016__chapter_b_public_domain', 'B-s8',     'External Lighting',                     9,  9, 2),
  ('Inner_West_Ashfield_DCP_2016__chapter_b_public_domain', 'B-s9-10',  'Undergrounding and Public Art',        10, 10, 2)
ON CONFLICT DO NOTHING;

-- ── chapter_e2_haberfield ────────────────────────────────────────────────────

-- Remove catch-all entry (DQ-28 resolution)
DELETE FROM dcp_table_of_contents
WHERE document_id = 'Inner_West_Ashfield_DCP_2016__chapter_e2_haberfield';

-- Insert 17 per-section entries matching COUNCIL_CHAPTER_RANGES
-- Verified from PDF via inspect_e2_sections.py (2026-03-31)
INSERT INTO dcp_table_of_contents
  (document_id, section_number, section_title, page_start, page_end, depth)
VALUES
  ('Inner_West_Ashfield_DCP_2016__chapter_e2_haberfield', 'E2-intro',    'Introduction',                        1,  2, 1),
  ('Inner_West_Ashfield_DCP_2016__chapter_e2_haberfield', 'E2-s2-1',     'Desired Future Character',            3,  4, 2),
  ('Inner_West_Ashfield_DCP_2016__chapter_e2_haberfield', 'E2-s2-2-3',   'General and Pattern of Development',  5,  5, 2),
  ('Inner_West_Ashfield_DCP_2016__chapter_e2_haberfield', 'E2-s2-4',     'Building Form',                       6,  6, 2),
  ('Inner_West_Ashfield_DCP_2016__chapter_e2_haberfield', 'E2-s2-5',     'Roof Forms',                          7,  7, 2),
  ('Inner_West_Ashfield_DCP_2016__chapter_e2_haberfield', 'E2-s2-6',     'Siting Setbacks and Levels',          8,  8, 2),
  ('Inner_West_Ashfield_DCP_2016__chapter_e2_haberfield', 'E2-s2-7',     'Walls',                               9,  9, 2),
  ('Inner_West_Ashfield_DCP_2016__chapter_e2_haberfield', 'E2-s2-8-9',   'Chimneys and Joinery',               10, 10, 2),
  ('Inner_West_Ashfield_DCP_2016__chapter_e2_haberfield', 'E2-s2-10',    'Windows and Doors',                  11, 11, 2),
  ('Inner_West_Ashfield_DCP_2016__chapter_e2_haberfield', 'E2-s2-11-12', 'Window Sunhoods and Verandahs',      12, 12, 2),
  ('Inner_West_Ashfield_DCP_2016__chapter_e2_haberfield', 'E2-s2-13',    'Garages and Carports',               13, 13, 2),
  ('Inner_West_Ashfield_DCP_2016__chapter_e2_haberfield', 'E2-s2-14-15', 'Outbuildings and Colour Schemes',    14, 14, 2),
  ('Inner_West_Ashfield_DCP_2016__chapter_e2_haberfield', 'E2-s2-16',    'Fences and Gates',                   15, 15, 2),
  ('Inner_West_Ashfield_DCP_2016__chapter_e2_haberfield', 'E2-s2-17',    'Garden Elements',                    16, 16, 2),
  ('Inner_West_Ashfield_DCP_2016__chapter_e2_haberfield', 'E2-s2-18-19', 'Modern Technology and Commercial',   17, 18, 2),
  ('Inner_West_Ashfield_DCP_2016__chapter_e2_haberfield', 'E2-s2-20',    'Non-Conforming Houses',              19, 19, 2),
  ('Inner_West_Ashfield_DCP_2016__chapter_e2_haberfield', 'E2-s2-21',    'New Dwellings',                      20, 22, 2)
ON CONFLICT DO NOTHING;

COMMIT;
