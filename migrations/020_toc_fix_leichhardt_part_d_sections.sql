-- Migration 020: Add missing Section 1 (Energy) for Leichhardt Part D
--               and fix Section 2 page_start from 1 to 6
--
-- Problem: Part D TOC only had one entry (SECTION 2, pages 1-15) covering
--          the whole chapter. Section 1 (Energy Management, pages 3–5) was
--          never extracted. All 89 provisions mapped to one section key
--          (Part D::SECTION 2), causing the DA sidebar to show "0 of 1 assessed"
--          for an 89-provision chapter.
--
-- Fix:
--   1. Fix SECTION 2 page_start from 1 → 6 (waste management starts at page 6)
--   2. Insert SECTION 1 covering pages 1-5 (energy management)
--
-- Applies to both the space-format and underscore-format document_ids.
-- (Underscore-format provisions are is_current=FALSE after migration 019,
--  but the TOC entries are kept for JOIN correctness.)

BEGIN;

-- Fix Section 2 page_start: was 1 (the whole chapter), should be 6
UPDATE dcp_table_of_contents
SET page_start = 6
WHERE document_id IN (
  'Leichhardt DCP 2013 - 9 - Part D Energy - with IWLEP 2022 amendments',
  'Leichhardt_DCP_2013__part_d_energy'
)
AND section_number = 'SECTION 2';

-- Insert Section 1: Energy Management (pages 1-5)
INSERT INTO dcp_table_of_contents
  (document_id, section_number, section_title, page_start, page_end, depth)
VALUES
  ('Leichhardt DCP 2013 - 9 - Part D Energy - with IWLEP 2022 amendments',
   'SECTION 1', 'ENERGY MANAGEMENT', 1, 5, 1),
  ('Leichhardt_DCP_2013__part_d_energy',
   'SECTION 1', 'ENERGY MANAGEMENT', 1, 5, 1)
ON CONFLICT DO NOTHING;

COMMIT;
