-- Migration: Tag LEP provisions with development-type-specific rules
-- Handles exceptions like "residential flats can be 12m"

-- ANALYSIS:
-- Found 41 LEP provisions mentioning "residential flat"
-- Found 11 LEP provisions mentioning "dwelling house"
-- Found 12 LEP provisions mentioning "multi dwelling"
-- Found 24 LEP provisions mentioning "boarding house"
-- Found 16 LEP provisions mentioning "secondary dwelling"

BEGIN;

-- Tag residential flat building provisions
UPDATE regulatory_provisions
SET development_type = 'residential_flat_building'
WHERE document_id LIKE '%LEP%'
  AND development_type IS NULL
  AND (
    LOWER(provision_text) LIKE '%residential flat building%'
    OR LOWER(provision_text) LIKE '%residential flat buildings%'
  );

-- Tag dwelling house provisions
UPDATE regulatory_provisions
SET development_type = 'dwelling_house'
WHERE document_id LIKE '%LEP%'
  AND development_type IS NULL
  AND LOWER(provision_text) LIKE '%dwelling house%'
  AND NOT (
    -- Exclude general provisions that just mention dwelling houses
    LOWER(provision_text) LIKE '%including dwelling house%'
    OR LOWER(provision_text) LIKE '%such as dwelling house%'
  );

-- Tag multi dwelling provisions
UPDATE regulatory_provisions
SET development_type = 'multi_dwelling'
WHERE document_id LIKE '%LEP%'
  AND development_type IS NULL
  AND (
    LOWER(provision_text) LIKE '%multi dwelling housing%'
    OR LOWER(provision_text) LIKE '%multi-dwelling housing%'
  );

-- Tag shop top housing provisions
UPDATE regulatory_provisions
SET development_type = 'shop_top_housing'
WHERE document_id LIKE '%LEP%'
  AND development_type IS NULL
  AND LOWER(provision_text) LIKE '%shop top housing%';

-- Tag boarding house provisions
UPDATE regulatory_provisions
SET development_type = 'boarding_house'
WHERE document_id LIKE '%LEP%'
  AND development_type IS NULL
  AND LOWER(provision_text) LIKE '%boarding house%';

-- Tag secondary dwelling provisions
UPDATE regulatory_provisions
SET development_type = 'secondary_dwelling'
WHERE document_id LIKE '%LEP%'
  AND development_type IS NULL
  AND (
    LOWER(provision_text) LIKE '%secondary dwelling%'
    OR LOWER(provision_text) LIKE '%ancillary dwelling%'
  );

-- Tag commercial provisions
UPDATE regulatory_provisions
SET development_type = 'commercial'
WHERE document_id LIKE '%LEP%'
  AND development_type IS NULL
  AND (
    LOWER(provision_text) LIKE '%commercial premises%'
    OR LOWER(provision_text) LIKE '%commercial development%'
  )
  AND NOT (
    -- Exclude general zoning provisions
    LOWER(provision_text) LIKE '%zone%'
    AND LOWER(provision_text) LIKE '%permitted%'
  );

-- Report results
SELECT
    development_type,
    COUNT(*) as newly_tagged,
    COUNT(*) * 100.0 / (SELECT COUNT(*) FROM regulatory_provisions WHERE document_id LIKE '%LEP%') as percentage
FROM regulatory_provisions
WHERE document_id LIKE '%LEP%'
  AND development_type IS NOT NULL
GROUP BY development_type
ORDER BY newly_tagged DESC;

COMMIT;

-- NOTE: This is a conservative approach that only tags provisions with explicit dev type mentions.
-- Most LEP provisions (height, FSR) apply to ALL dev types and should remain untagged.

-- Usage in API:
-- SELECT * FROM regulatory_provisions
-- WHERE document_id LIKE '%LEP%'
--   AND (development_type = 'residential_flat_building' OR development_type IS NULL);