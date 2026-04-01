BEGIN;

-- Migration 023: r2_pdf_url for ADG requirements and E&C documents
--
-- ADG: sepp_adg_requirements gets r2_pdf_url pointing to full combined ADG PDF (182pp).
--      source_page values (13–143) are direct PDF page numbers in that file.
--
-- E&C: documents table gets r2_pdf_url. All 69 E&C document rows point to the same
--      extraction origin PDF (454pp, July 2025). pdf_page on regulatory_provisions
--      is correct for that version. Frontend joins documents to get url at query time.

-- ADG
ALTER TABLE sepp_adg_requirements
  ADD COLUMN IF NOT EXISTS r2_pdf_url TEXT;

UPDATE sepp_adg_requirements
SET r2_pdf_url = 'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/source-pdfs/adgs/v1.0-baseline/apartment-design-guide.pdf';

-- Null stale PNG image URLs
UPDATE sepp_adg_requirements SET pdf_page_image_url = NULL;

-- E&C documents
ALTER TABLE documents
  ADD COLUMN IF NOT EXISTS r2_pdf_url TEXT;

UPDATE documents
SET r2_pdf_url = 'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/source-pdfs/sepps/v1.0-baseline/sepp-exempt-complying-2008.pdf'
WHERE pdf_name ILIKE '%Exempt and Complying%';

COMMIT;
