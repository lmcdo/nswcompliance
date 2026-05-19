-- Migration 044: Expand extraction_method CHECK constraint
-- Current CHECK allows: 'text_extraction', 'mistral_ocr', 'manual'
-- Expand to include values used by insert scripts and extractors:
--   'manual_insert', 'manual_curation', 'gpt4_extraction', 'automatic_extraction'
-- All existing rows already have valid values (no backfill needed).

ALTER TABLE dcp_setback_controls
  DROP CONSTRAINT IF EXISTS dcp_setback_controls_extraction_method_check;

ALTER TABLE dcp_setback_controls
  ADD CONSTRAINT dcp_setback_controls_extraction_method_check CHECK (
    extraction_method IN (
      'text_extraction',
      'mistral_ocr',
      'manual',
      'manual_insert',
      'manual_curation',
      'gpt4_extraction',
      'automatic_extraction'
    )
  );

-- Ensure extraction_method is NOT NULL (already true for all 895 rows)
ALTER TABLE dcp_setback_controls
  ALTER COLUMN extraction_method SET NOT NULL;

-- Set a sensible default for future inserts that forget to specify
ALTER TABLE dcp_setback_controls
  ALTER COLUMN extraction_method SET DEFAULT 'manual_insert';
