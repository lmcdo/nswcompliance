-- Migration 032: Add versioning + extraction audit to dcp_setback_controls
-- dcp_version: matches r2_current_path segment e.g. 'v1.1-2026-03-02'
-- is_current: FALSE when superseded by a newer DCP version
-- extraction_method: audit trail for data confidence

ALTER TABLE dcp_setback_controls
  ADD COLUMN IF NOT EXISTS dcp_version       text,
  ADD COLUMN IF NOT EXISTS is_current        boolean NOT NULL DEFAULT TRUE,
  ADD COLUMN IF NOT EXISTS extraction_method text CHECK (
    extraction_method IN ('text_extraction', 'mistral_ocr', 'manual')
  );

-- Index for active-only queries (the common case)
CREATE INDEX IF NOT EXISTS dcp_setback_controls_current
  ON dcp_setback_controls(lga, dev_type, is_current)
  WHERE is_current = TRUE;

COMMENT ON COLUMN dcp_setback_controls.dcp_version IS
  'DCP version string matching dcp_chapter_registry r2_current_path segment, e.g. v1.1-2026-03-02';

COMMENT ON COLUMN dcp_setback_controls.is_current IS
  'FALSE when superseded by a newer extraction after a DCP amendment. Query WHERE is_current = TRUE.';

COMMENT ON COLUMN dcp_setback_controls.extraction_method IS
  'text_extraction: from regulatory_provisions.provision_text via NumericExtractor. '
  'mistral_ocr: from Mistral OCR 3 on source PDF. '
  'manual: read from PDF and inserted directly.';
