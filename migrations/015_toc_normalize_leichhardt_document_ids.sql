-- Migration 015: Normalize Leichhardt dcp_table_of_contents document_ids
--
-- Problem: TOC entries use old document_id format (e.g. "Leichhardt_DCP_2013__3__Part_A__Introduction__...")
--          Provisions use new format (e.g. "Leichhardt_DCP_2013__part_a_introduction")
--          The enrichWithTocSections JOIN fails to match, so toc_section_number is always NULL
--          for Leichhardt provisions → all provisions collapse to "General provisions" bucket.
--
-- Fix: UPDATE document_id on TOC entries to match provision document_ids.
--      Delete duplicate "Reduced_Size" variant (same content as with_IWLEP version).
--
-- Rollback: UPDATE document_id back to old values (kept in comments below).
-- Safe: No provision data is touched. Only dcp_table_of_contents.document_id is changed.

BEGIN;

-- Verify row counts before (for rollback verification)
-- SELECT COUNT(*) FROM dcp_table_of_contents WHERE document_id LIKE '%eichhardt%';
-- Expected: 20 entries before, 19 after (1 duplicate deleted)

-- Part A
UPDATE dcp_table_of_contents
SET document_id = 'Leichhardt_DCP_2013__part_a_introduction'
WHERE document_id = 'Leichhardt_DCP_2013__3__Part_A__Introduction__with_IWLEP_2022_amendments';

-- Part B
UPDATE dcp_table_of_contents
SET document_id = 'Leichhardt_DCP_2013__part_b_connections'
WHERE document_id = 'Leichhardt_DCP_2013__4__Part_B_Connections__with_IWLEP_2022_amendments';

-- Part C Section 1
UPDATE dcp_table_of_contents
SET document_id = 'Leichhardt_DCP_2013__part_c_s1_general'
WHERE document_id = 'Leichhardt_DCP_2013__5__Part_C_Place_Section_1__with_IWLEP_2022_amendments_March_23';

-- Part C Section 2: delete the "Reduced_Size" duplicate (same content, stale copy)
DELETE FROM dcp_table_of_contents
WHERE document_id = 'Leichhardt_DCP_2013__6__Part_C_Place_Section_2__Reduced_Size';

-- Part C Section 2: keep the authoritative IWLEP version
UPDATE dcp_table_of_contents
SET document_id = 'Leichhardt_DCP_2013__part_c_s2_urban_character'
WHERE document_id = 'Leichhardt_DCP_2013__6__Part_C_Place_Section_2__with_IWLEP_2022_amendments';

-- Part C Section 3
UPDATE dcp_table_of_contents
SET document_id = 'Leichhardt_DCP_2013__part_c_s3_residential'
WHERE document_id = 'Leichhardt_DCP_2013__7__Part_C_Place_Section_3__with_IWLEP_2022_amendments';

-- Part C Section 4
UPDATE dcp_table_of_contents
SET document_id = 'Leichhardt_DCP_2013__part_c_s4_non_residential'
WHERE document_id = 'Leichhardt_DCP_2013__8__Part_C_Place_Section_4__with_IWLEP_2022_amendments';

-- Part C Section 5 (different naming convention)
UPDATE dcp_table_of_contents
SET document_id = 'Leichhardt_DCP_2013__part_c_s5_entertainment_precincts'
WHERE document_id = 'Leichhardt_DCP_2013_Part_C_Section_5';

-- Part D
UPDATE dcp_table_of_contents
SET document_id = 'Leichhardt_DCP_2013__part_d_energy'
WHERE document_id = 'Leichhardt_DCP_2013__9__Part_D_Energy__with_IWLEP_2022_amendments';

-- Part E
UPDATE dcp_table_of_contents
SET document_id = 'Leichhardt_DCP_2013__part_e_water'
WHERE document_id = 'Leichhardt_DCP_2013__10__Part_E_Water__with_IWLEP_2022_amendments';

-- Part F
UPDATE dcp_table_of_contents
SET document_id = 'Leichhardt_DCP_2013__part_f_food'
WHERE document_id = 'Leichhardt_DCP_2013__11__Part_F_Food__with_IWLEP_2022_amendments';

-- Part G Section 1-12 (split across 3 PDFs — all map to same provision document_id)
UPDATE dcp_table_of_contents
SET document_id = 'Leichhardt_DCP_2013__part_g_s1_site_specific'
WHERE document_id IN (
  'Leichhardt_DCP_2013__12__Part_G_Section_1_12__Amdt_19__Nov_2023_1_50',
  'Leichhardt_DCP_2013__12__Part_G_Section_1_12__Amdt_19__Nov_2023_51_100',
  'Leichhardt_DCP_2013__12__Part_G_Section_1_12__Amdt_19__Nov_2023_101_149'
);

-- Part G Section 13 (Pyrmont Bridge Road)
UPDATE dcp_table_of_contents
SET document_id = 'Leichhardt_DCP_2013__part_g_s13_pyrmont_bridge_rd'
WHERE document_id = 'Leichhardt_DCP_2013__12__Part_G_Section_13__Amdt_19__Pyrmont_Bridge_Road_Nov_2023';

-- Appendix B
UPDATE dcp_table_of_contents
SET document_id = 'Leichhardt_DCP_2013__appendix_b_building_typologies'
WHERE document_id = 'Leichhardt_DCP_2013__14__Appendix_B_Building_Typologies__with_IWLEP_2022_amendments';

-- Note: Appendix A (Glossary), Appendix C, Appendix E have no matching provision document_ids
-- and are not updated — they will remain with old document_ids and not affect any JOIN.

COMMIT;
