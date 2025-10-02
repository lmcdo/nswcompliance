-- Migration: Create LGA-independent DCP section mapping system
-- Automatically extracts DCP structure from existing documents
-- Scales to any new LGA without code changes

-- ============================================================================
-- PART 1: Create DCP Section Mappings Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS dcp_section_mappings (
  id SERIAL PRIMARY KEY,
  lga TEXT NOT NULL,                        -- e.g., "Inner West", "Canterbury-Bankstown"
  document_id TEXT NOT NULL,                -- Full DCP document ID
  development_type TEXT NOT NULL,           -- e.g., "dwelling_house", "multi_dwelling"
  section_identifier TEXT NOT NULL,         -- e.g., "F.1", "3.1", "Part A.2"
  section_title TEXT,                       -- e.g., "Dwelling Houses"
  applicable_zones TEXT[],                  -- Array of zones: ['R1','R2','R3','R4']
  created_at TIMESTAMP DEFAULT NOW(),
  last_updated TIMESTAMP DEFAULT NOW(),
  UNIQUE(lga, development_type, document_id)
);

CREATE INDEX idx_dcp_section_lga ON dcp_section_mappings(lga);
CREATE INDEX idx_dcp_section_devtype ON dcp_section_mappings(development_type);
CREATE INDEX idx_dcp_section_lookup ON dcp_section_mappings(lga, development_type);

-- ============================================================================
-- PART 2: Auto-populate from existing provisions
-- ============================================================================

-- Extract DCP section structure from provisions_with_category
-- This works for ANY LGA that has DCP provisions in the database

INSERT INTO dcp_section_mappings (lga, document_id, development_type, section_identifier, section_title, applicable_zones)
SELECT DISTINCT
  -- Extract LGA from document_id (e.g., "Inner_West_Ashfield_DCP" -> "Inner West")
  CASE
    WHEN document_id LIKE '%Inner_West%' OR document_id LIKE '%Inner West%' THEN 'Inner West'
    WHEN document_id LIKE '%Canterbury%Bankstown%' THEN 'Canterbury-Bankstown'
    WHEN document_id LIKE '%Sydney%' THEN 'Sydney'
    WHEN document_id LIKE '%Marrickville%' THEN 'Marrickville'
    WHEN document_id LIKE '%Ashfield%' THEN 'Ashfield'
    WHEN document_id LIKE '%Leichhardt%' THEN 'Leichhardt'
    ELSE SUBSTRING(document_id FROM 1 FOR POSITION('_' IN document_id) - 1)
  END as lga,

  document_id,
  development_type,

  -- Extract section identifier (e.g., "F.1" from "F.1 Dwelling Houses")
  CASE
    WHEN section_header ~ '^[A-Z]\.\d+' THEN SUBSTRING(section_header FROM '^[A-Z]\.\d+')
    WHEN section_header ~ '^\d+\.\d+' THEN SUBSTRING(section_header FROM '^\d+\.\d+')
    WHEN ref_number IS NOT NULL THEN ref_number
    ELSE 'UNKNOWN'
  END as section_identifier,

  section_header as section_title,

  -- Infer applicable zones (default to common residential zones)
  CASE
    WHEN development_type IN ('dwelling_house', 'secondary_dwelling', 'dual_occupancy') THEN ARRAY['R1','R2','R3','R4','R5']
    WHEN development_type IN ('multi_dwelling', 'residential_flat') THEN ARRAY['R2','R3','R4','B1','B2','B4']
    WHEN development_type IN ('boarding_house', 'residential_care', 'child_care') THEN ARRAY['R1','R2','R3','R4','B1','B2','B4']
    WHEN development_type = 'commercial' THEN ARRAY['B1','B2','B3','B4','B5','B6','IN1','IN2']
    WHEN development_type = 'shop_top_housing' THEN ARRAY['B1','B2','B4']
    ELSE ARRAY['R2','R3','R4']  -- Default residential zones
  END as applicable_zones

FROM provisions_with_category
WHERE document_category = 'DCP'
  AND development_type IS NOT NULL
  AND section_header IS NOT NULL
  AND section_header != ''
ON CONFLICT (lga, development_type, document_id) DO NOTHING;

-- ============================================================================
-- PART 3: Create view for easy lookup
-- ============================================================================

CREATE OR REPLACE VIEW dcp_section_lookup AS
SELECT
  lga,
  development_type,
  section_identifier,
  section_title,
  applicable_zones,
  document_id,
  -- Add helper column: does this section apply to a specific zone?
  CASE
    WHEN '*' = ANY(applicable_zones) THEN TRUE
    ELSE NULL  -- Will need to check zone in query
  END as applies_to_all_zones
FROM dcp_section_mappings
ORDER BY lga, development_type;

-- ============================================================================
-- PART 4: Function to get DCP section for any LGA + dev type + zone
-- ============================================================================

CREATE OR REPLACE FUNCTION get_dcp_section(
  p_lga TEXT,
  p_zone TEXT,
  p_dev_type TEXT
) RETURNS TABLE(
  section_identifier TEXT,
  section_title TEXT,
  document_id TEXT
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    dsm.section_identifier,
    dsm.section_title,
    dsm.document_id
  FROM dcp_section_mappings dsm
  WHERE dsm.lga = p_lga
    AND dsm.development_type = p_dev_type
    AND (
      p_zone = ANY(dsm.applicable_zones)
      OR '*' = ANY(dsm.applicable_zones)
    )
  LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- PART 5: Test queries
-- ============================================================================

-- Test 1: Get all DCP sections for Inner West
SELECT * FROM dcp_section_mappings WHERE lga = 'Inner West';

-- Test 2: Get DCP section for specific scenario
SELECT * FROM get_dcp_section('Inner West', 'R2', 'dwelling_house');

-- Test 3: Get all development types available in each LGA
SELECT lga, COUNT(DISTINCT development_type) as dev_types_count
FROM dcp_section_mappings
GROUP BY lga
ORDER BY dev_types_count DESC;

-- ============================================================================
-- PART 6: Manual overrides table (for edge cases)
-- ============================================================================

CREATE TABLE IF NOT EXISTS dcp_section_overrides (
  id SERIAL PRIMARY KEY,
  lga TEXT NOT NULL,
  document_id TEXT NOT NULL,
  development_type TEXT NOT NULL,
  zone TEXT NOT NULL,
  override_section TEXT NOT NULL,
  reason TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(lga, development_type, zone, document_id)
);

-- Example override: Special zone rules
-- INSERT INTO dcp_section_overrides (lga, document_id, development_type, zone, override_section, reason)
-- VALUES ('Inner West', 'Inner_West_Ashfield_DCP_2016', 'dwelling_house', 'R1', 'F.1A', 'Heritage overlay zone');

COMMIT;

-- ============================================================================
-- USAGE IN API
-- ============================================================================

/*
Instead of:
  const dcpSection = getDCPSection(zone, devType);  // Hard-coded function

Use:
  SELECT * FROM get_dcp_section($1, $2, $3);
  Parameters: [lga, zone, devType]

Example:
  SELECT * FROM get_dcp_section('Inner West', 'R2', 'dwelling_house');
  Returns: { section_identifier: 'F.1', section_title: 'Dwelling Houses', document_id: 'Inner_West_...' }
*/