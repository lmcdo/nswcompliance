-- Migration 038: Add detected_category to dcp_chapter_registry
-- Classifies auto-detected chapters so the monitor can auto-handle
-- obvious non-provision PDFs (maps, repealed docs, cover pages) and
-- only surface real text chapters for review.

ALTER TABLE dcp_chapter_registry
    ADD COLUMN IF NOT EXISTS detected_category TEXT;

-- Also replace hub_expected_count with hub_last_pdf_count
-- (tracks actual PDF count from last scrape for delta detection)
ALTER TABLE dcp_chapter_registry
    ADD COLUMN IF NOT EXISTS hub_last_pdf_count INTEGER;

COMMENT ON COLUMN dcp_chapter_registry.detected_category IS
    'Auto-classification: spatial, repealed, inert, guide, text, unknown. Set on auto-detection.';

COMMENT ON COLUMN dcp_chapter_registry.hub_last_pdf_count IS
    'Actual PDF count from last hub scrape. Used for delta detection instead of static hub_expected_count.';

-- Backfill existing auto_detected rows based on label patterns
UPDATE dcp_chapter_registry
SET detected_category = CASE
    WHEN chapter_label ~* '(^sheet\s+\d|map$|map\s|frontage.+map|height.+map|setback.+map|signage.+map|lane.+map|link.+map|priority.+map|stormwater.+map|trading.+map|open\s+space.+map|colonnades.+map|contributions.+map|sound\s+management$|domain\s+setback)'
        THEN 'spatial'
    WHEN chapter_label ~* '^repealed'
        THEN 'repealed'
    WHEN chapter_label ~* '(^table\s+of\s+contents|^preliminary|^document\s+information|^section\s+1\s.*preliminary)'
        THEN 'inert'
    WHEN chapter_label ~* '(guide([^a-z]|$)|manual([^a-z]|$)|character\s+statement|waste\s+design)'
        THEN 'guide'
    WHEN chapter_label ~* '(^chapter\s+[A-Za-z]?\d|^part\s+\d|^section\s+\d)'
        THEN 'text'
    ELSE 'unknown'
END
WHERE registration_status = 'auto_detected'
  AND detected_category IS NULL;

-- Auto-handle: reject repealed, mark spatial as spatial, mark inert as inert
UPDATE dcp_chapter_registry
SET registration_status = 'rejected',
    updated_at = NOW()
WHERE registration_status = 'auto_detected'
  AND detected_category = 'repealed';

UPDATE dcp_chapter_registry
SET registration_status = 'confirmed',
    is_active = TRUE,
    is_spatial = TRUE,
    needs_extraction = FALSE,
    updated_at = NOW()
WHERE registration_status = 'auto_detected'
  AND detected_category = 'spatial';

UPDATE dcp_chapter_registry
SET registration_status = 'confirmed',
    is_active = TRUE,
    is_inert = TRUE,
    needs_extraction = FALSE,
    updated_at = NOW()
WHERE registration_status = 'auto_detected'
  AND detected_category = 'inert';
