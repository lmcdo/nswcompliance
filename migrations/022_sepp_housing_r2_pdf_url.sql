BEGIN;

-- Migration 022: add r2_pdf_url to housing_sepp_standards
-- Replaces per-page PNG image approach (pdf_page_image_url) with whole-PDF + page number.
-- Same pattern as Waverley DCP. Frontend opens PDF at #page=N in new tab.

ALTER TABLE housing_sepp_standards
  ADD COLUMN IF NOT EXISTS r2_pdf_url TEXT;

UPDATE housing_sepp_standards
SET r2_pdf_url = 'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/source-pdfs/sepps/v1.0-baseline/sepp-housing-2021.pdf';

-- pdf_page_image_url retained but nulled — PNG extractions are from an old version
UPDATE housing_sepp_standards SET pdf_page_image_url = NULL;

COMMIT;
