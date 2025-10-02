-- Migration: Tag DCP provisions with development types based on section headers
-- Run time: ~1-2 seconds for 15K provisions
-- Safe: Only UPDATEs where development_type IS NULL

BEGIN;

-- Dwelling houses
UPDATE regulatory_provisions
SET development_type = 'dwelling_house'
WHERE document_id LIKE '%DCP%'
  AND development_type IS NULL
  AND (
    LOWER(section_header) LIKE '%dwelling house%'
    OR LOWER(section_header) LIKE '%single dwelling%'
    OR section_header LIKE '%F.1%'
    OR section_header LIKE '%3.1 %'
  );

-- Secondary dwellings
UPDATE regulatory_provisions
SET development_type = 'secondary_dwelling'
WHERE document_id LIKE '%DCP%'
  AND development_type IS NULL
  AND (
    LOWER(section_header) LIKE '%secondary dwelling%'
    OR section_header LIKE '%F.2%'
    OR section_header LIKE '%3.2 %'
  );

-- Shop top housing
UPDATE regulatory_provisions
SET development_type = 'shop_top_housing'
WHERE document_id LIKE '%DCP%'
  AND development_type IS NULL
  AND (
    LOWER(section_header) LIKE '%shop top%'
    OR section_header LIKE '%F.3%'
    OR section_header LIKE '%3.3 %'
  );

-- Multi dwelling housing
UPDATE regulatory_provisions
SET development_type = 'multi_dwelling'
WHERE document_id LIKE '%DCP%'
  AND development_type IS NULL
  AND (
    LOWER(section_header) LIKE '%multi dwelling%'
    OR LOWER(section_header) LIKE '%multi-dwelling%'
    OR section_header LIKE '%F.4%'
    OR section_header LIKE '%3.4 %'
  );

-- Residential flat buildings
UPDATE regulatory_provisions
SET development_type = 'residential_flat_building'
WHERE document_id LIKE '%DCP%'
  AND development_type IS NULL
  AND (
    LOWER(section_header) LIKE '%residential flat%'
    OR LOWER(section_header) LIKE '%rfb%'
    OR section_header LIKE '%F.5%'
    OR section_header LIKE '%3.5 %'
  );

-- Boarding houses
UPDATE regulatory_provisions
SET development_type = 'boarding_house'
WHERE document_id LIKE '%DCP%'
  AND development_type IS NULL
  AND (
    LOWER(section_header) LIKE '%boarding house%'
    OR section_header LIKE '%F.6%'
    OR section_header LIKE '%3.6 %'
  );

-- Residential care facilities
UPDATE regulatory_provisions
SET development_type = 'residential_care'
WHERE document_id LIKE '%DCP%'
  AND development_type IS NULL
  AND (
    LOWER(section_header) LIKE '%residential care%'
    OR LOWER(section_header) LIKE '%aged care%'
    OR section_header LIKE '%F.7%'
    OR section_header LIKE '%3.7 %'
  );

-- Child care centres
UPDATE regulatory_provisions
SET development_type = 'child_care'
WHERE document_id LIKE '%DCP%'
  AND development_type IS NULL
  AND (
    LOWER(section_header) LIKE '%child care%'
    OR LOWER(section_header) LIKE '%childcare%'
    OR section_header LIKE '%F.8%'
    OR section_header LIKE '%3.8 %'
  );

-- Commercial premises
UPDATE regulatory_provisions
SET development_type = 'commercial'
WHERE document_id LIKE '%DCP%'
  AND development_type IS NULL
  AND (
    LOWER(section_header) LIKE '%commercial%'
    OR section_header LIKE '%F.9%'
    OR section_header LIKE '%3.9 %'
  );

-- Dual occupancy
UPDATE regulatory_provisions
SET development_type = 'dual_occupancy'
WHERE document_id LIKE '%DCP%'
  AND development_type IS NULL
  AND LOWER(section_header) LIKE '%dual occupancy%';

-- Townhouses
UPDATE regulatory_provisions
SET development_type = 'townhouse'
WHERE document_id LIKE '%DCP%'
  AND development_type IS NULL
  AND LOWER(section_header) LIKE '%townhouse%';

-- Report results
SELECT
  development_type,
  COUNT(*) as newly_tagged
FROM regulatory_provisions
WHERE document_id LIKE '%DCP%'
  AND development_type IS NOT NULL
GROUP BY development_type
ORDER BY newly_tagged DESC;

COMMIT;