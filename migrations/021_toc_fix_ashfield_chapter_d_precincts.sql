-- Migration 021: Ashfield chapter_d_precinct_guidelines — add per-precinct TOC entries
--
-- Problem: chapter_d had one coarse entry (sec=1 "Precinct Guidelines", pages 1-204)
--          covering all 564 provisions in 8 distinct precincts.
--          DA mode showed "0 of 1 assessed" for a 564-provision chapter.
--
-- Root cause: TOC extractor captured only the top-level chapter heading, not
--             the 8 precinct sub-sections (D-Part1 through D-Part8).
--
-- The extractor assigned all provisions in each precinct to that precinct's
-- first page (verified from DB: 8 distinct pages only):
--   p3   D-Part1 Ashfield Town Centre   (101 provisions)
--   p43  D-Part2 Ashfield East          (45 provisions)
--   p60  D-Part3 Croydon South          (66 provisions)
--   p86  D-Part4 Haberfield             (102 provisions)
--   p112 D-Part5 Hurlstone Park         (101 provisions)
--   p158 D-Part6 Summer Hill            (34 provisions)
--   p171 D-Part7 Ashfield South         (67 provisions)
--   p182 D-Part8 Canterbury Road        (48 provisions)
--
-- Fix:
--   1. Delete the coarse entry (replaces with 8 precise entries below)
--   2. Insert 8 sub-section entries, each covering its page range

BEGIN;

-- Remove coarse catch-all entry
DELETE FROM dcp_table_of_contents
WHERE document_id = 'Inner_West_Ashfield_DCP_2016__chapter_d_precinct_guidelines'
  AND section_number = '1'
  AND page_start = 1
  AND page_end = 204;

-- Insert 8 precinct sub-sections
INSERT INTO dcp_table_of_contents
  (document_id, section_number, section_title, page_start, page_end, depth)
VALUES
  ('Inner_West_Ashfield_DCP_2016__chapter_d_precinct_guidelines', 'D-Part1', 'Ashfield Town Centre',   1,   42, 2),
  ('Inner_West_Ashfield_DCP_2016__chapter_d_precinct_guidelines', 'D-Part2', 'Ashfield East',         43,   59, 2),
  ('Inner_West_Ashfield_DCP_2016__chapter_d_precinct_guidelines', 'D-Part3', 'Croydon South',         60,   85, 2),
  ('Inner_West_Ashfield_DCP_2016__chapter_d_precinct_guidelines', 'D-Part4', 'Haberfield',            86,  111, 2),
  ('Inner_West_Ashfield_DCP_2016__chapter_d_precinct_guidelines', 'D-Part5', 'Hurlstone Park',       112,  157, 2),
  ('Inner_West_Ashfield_DCP_2016__chapter_d_precinct_guidelines', 'D-Part6', 'Summer Hill',          158,  170, 2),
  ('Inner_West_Ashfield_DCP_2016__chapter_d_precinct_guidelines', 'D-Part7', 'Ashfield South',       171,  181, 2),
  ('Inner_West_Ashfield_DCP_2016__chapter_d_precinct_guidelines', 'D-Part8', 'Canterbury Road',      182,  204, 2)
ON CONFLICT DO NOTHING;

COMMIT;
