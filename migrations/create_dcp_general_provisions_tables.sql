-- Migration: Create DCP General Provisions Tables
-- Purpose: Store zone/development-type based general DCP controls (Chapter F)
-- Author: Claude Code
-- Date: 2025-10-28

-- ============================================================================
-- TABLE 1: dcp_general_provisions
-- Stores raw provisions from Chapter F with zone/devtype arrays
-- ============================================================================

CREATE TABLE IF NOT EXISTS dcp_general_provisions (
    id SERIAL PRIMARY KEY,
    lga TEXT NOT NULL,
    dcp_chapter TEXT NOT NULL,           -- 'F', 'Chapter F'
    part_number TEXT NOT NULL,           -- 'F1', 'F4', 'F5', etc.
    part_name TEXT,                      -- 'Dwelling Houses', 'Multi Dwelling Housing', etc.
    applicable_zones TEXT[],             -- ['R2', 'R3', 'R4']
    development_types TEXT[],            -- ['dwelling_house', 'alterations']
    section_header TEXT,
    provision_text TEXT NOT NULL,
    provision_type TEXT,                 -- 'setback', 'landscaping', 'building_form', etc.
    ref_number TEXT,
    display_order INT,
    document_id TEXT,
    pdf_path TEXT,
    pdf_page INT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for fast querying by zone and development type
CREATE INDEX IF NOT EXISTS idx_general_prov_lga
    ON dcp_general_provisions(lga);

CREATE INDEX IF NOT EXISTS idx_general_prov_zones
    ON dcp_general_provisions USING GIN(applicable_zones);

CREATE INDEX IF NOT EXISTS idx_general_prov_devtypes
    ON dcp_general_provisions USING GIN(development_types);

CREATE INDEX IF NOT EXISTS idx_general_prov_part
    ON dcp_general_provisions(lga, part_number);

CREATE INDEX IF NOT EXISTS idx_general_prov_document
    ON dcp_general_provisions(document_id);

-- Combined index for common query pattern
CREATE INDEX IF NOT EXISTS idx_general_prov_lga_zones_devtypes
    ON dcp_general_provisions(lga)
    WHERE applicable_zones IS NOT NULL
    AND development_types IS NOT NULL;

-- ============================================================================
-- TABLE 2: dcp_general_requirements
-- Stores LLM-categorized structured requirements from general provisions
-- ============================================================================

CREATE TABLE IF NOT EXISTS dcp_general_requirements (
    id SERIAL PRIMARY KEY,
    lga TEXT NOT NULL,
    applicable_zones TEXT[],             -- ['R2', 'R3', 'R4']
    development_types TEXT[],            -- ['dwelling_house', 'multi_dwelling']
    category TEXT NOT NULL,              -- 'setback_front', 'landscaping', etc.
    subcategory TEXT,                    -- Optional sub-classification
    requirement_text TEXT NOT NULL,
    value_numeric DECIMAL,               -- Numeric value if applicable
    value_min DECIMAL,                   -- Min value for ranges
    value_max DECIMAL,                   -- Max value for ranges
    unit TEXT,                           -- 'm', '%', 'spaces', etc.
    has_conditionals BOOLEAN DEFAULT FALSE,
    conditional_text TEXT,               -- "For lots >450m²", "In R3 zones", etc.
    source_provision_ids INTEGER[],      -- Array of dcp_general_provisions.id
    confidence TEXT,                     -- 'high', 'medium', 'low'
    confidence_score DECIMAL,
    extraction_context JSONB,            -- LLM reasoning, metadata
    processing_version TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for requirement queries
CREATE INDEX IF NOT EXISTS idx_general_req_lga
    ON dcp_general_requirements(lga);

CREATE INDEX IF NOT EXISTS idx_general_req_zones
    ON dcp_general_requirements USING GIN(applicable_zones);

CREATE INDEX IF NOT EXISTS idx_general_req_devtypes
    ON dcp_general_requirements USING GIN(development_types);

CREATE INDEX IF NOT EXISTS idx_general_req_category
    ON dcp_general_requirements(category);

CREATE INDEX IF NOT EXISTS idx_general_req_source
    ON dcp_general_requirements USING GIN(source_provision_ids);

-- Combined index for main query pattern
CREATE INDEX IF NOT EXISTS idx_general_req_lga_zones_devtypes
    ON dcp_general_requirements(lga)
    WHERE applicable_zones IS NOT NULL;

-- ============================================================================
-- HELPER VIEW: Combined general + precinct provisions
-- Makes it easy to query both tables at once
-- ============================================================================

CREATE OR REPLACE VIEW dcp_all_provisions AS
SELECT
    'general' as provision_source,
    id,
    lga,
    NULL as precinct_id,
    NULL as precinct_name,
    section_header,
    provision_text,
    provision_type,
    ref_number,
    display_order,
    document_id,
    applicable_zones,
    development_types,
    created_at
FROM dcp_general_provisions

UNION ALL

SELECT
    'precinct' as provision_source,
    id,
    lga,
    precinct_id,
    precinct_name,
    section_header,
    provision_text,
    provision_type,
    ref_number,
    display_order,
    document_id,
    NULL as applicable_zones,
    NULL as development_types,
    created_at
FROM dcp_precinct_provisions;

-- ============================================================================
-- COMMENTS for documentation
-- ============================================================================

COMMENT ON TABLE dcp_general_provisions IS
'General DCP provisions (e.g., Chapter F) that apply based on zone and development type, not geographic location';

COMMENT ON COLUMN dcp_general_provisions.applicable_zones IS
'Array of LEP zones this provision applies to (e.g., {R2,R3,R4}). NULL means applies to all zones.';

COMMENT ON COLUMN dcp_general_provisions.development_types IS
'Array of development types (e.g., {dwelling_house,secondary_dwelling}). NULL means applies to all types.';

COMMENT ON TABLE dcp_general_requirements IS
'LLM-categorized structured requirements extracted from general provisions for precise filtering';

COMMENT ON COLUMN dcp_general_requirements.source_provision_ids IS
'Array of IDs from dcp_general_provisions table that this requirement was extracted from';

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '✓ Migration complete: dcp_general_provisions tables created';
    RAISE NOTICE '✓ Tables: dcp_general_provisions, dcp_general_requirements';
    RAISE NOTICE '✓ Indexes: 11 indexes created for performance';
    RAISE NOTICE '✓ View: dcp_all_provisions created';
END $$;
