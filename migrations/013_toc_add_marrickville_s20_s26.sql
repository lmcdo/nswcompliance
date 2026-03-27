-- Migration 013: Add missing TOC entries for Marrickville DCP Part 2 sections s20–s26
-- Purpose: Provisions in these 6 chapters had no dcp_table_of_contents rows after
--   migration 011 updated existing TOC document_ids to new-clean format. Without TOC
--   entries, enrichWithTocSections returns null for toc_section_number, and the
--   grouping logic places these provisions in the "General" (unsectioned) bucket.
--
-- Sections affected:
--   s20 — Tree Management             (5 provisions, pages 1–9)
--   s21 — Site Facilities and Waste   (7 provisions, pages 1–34)
--   s22 — Flood Management            (3 provisions, pages 1–12)
--   s23 — Acid Sulfate Soils          (2 provisions, pages 1–8)
--   s24 — Contaminated Land           (5 provisions, pages 1–21)
--   s26 — Special Entertainment Precincts (5 provisions, pages 1–7)
--
-- Each chapter is a separate PDF (one document_id per chapter). A single TOC entry
-- per chapter with page_start=1, page_end=NULL covers all pages (open-ended range).
-- depth=1 = chapter level; part_number=2 = Part 2 of the DCP.
--
-- Verified: section numbers consistent with existing Part 2 TOC (s05→2.5, s10→2.10).
-- Verified: 2026-03-21

BEGIN;

INSERT INTO dcp_table_of_contents
  (document_id, section_number, section_title, page_start, page_end, part_number, depth, parent_section)
VALUES
  ('Marrickville_DCP_2011__part2_s20_tree_management',
   '2.20', 'Tree Management',
   1, NULL, 2, 1, NULL),

  ('Marrickville_DCP_2011__part2_s21_site_facilities_waste',
   '2.21', 'Site Facilities and Waste Management',
   1, NULL, 2, 1, NULL),

  ('Marrickville_DCP_2011__part2_s22_flood_management',
   '2.22', 'Flood Management',
   1, NULL, 2, 1, NULL),

  ('Marrickville_DCP_2011__part2_s23_acid_sulfate',
   '2.23', 'Acid Sulfate Soils',
   1, NULL, 2, 1, NULL),

  ('Marrickville_DCP_2011__part2_s24_contaminated_land',
   '2.24', 'Contaminated Land',
   1, NULL, 2, 1, NULL),

  ('Marrickville_DCP_2011__part2_s26_entertainment_precincts',
   '2.26', 'Special Entertainment Precincts',
   1, NULL, 2, 1, NULL);

COMMIT;

-- Verification query (run after applying):
-- SELECT document_id, section_number, section_title, page_start, page_end
-- FROM dcp_table_of_contents
-- WHERE document_id LIKE 'Marrickville_DCP_2011__part2_s2%'
-- ORDER BY section_number;
-- Expected: 6 rows, one per chapter above.
