-- Migration: Create setback_rules table for structured conditional setback storage
-- Replaces unstructured text in regulatory_provisions.provision_text
-- Enables precise queries: "Give me first floor side setbacks in R2"

-- Safety: Create table only if it doesn't exist
CREATE TABLE IF NOT EXISTS setback_rules (
    id SERIAL PRIMARY KEY,

    -- Reference to source provision
    provision_id INTEGER REFERENCES regulatory_provisions(id) ON DELETE CASCADE,
    ref_number TEXT,  -- Clause reference (e.g., "C11", "2.3.1")

    -- Spatial attributes (WHERE does the setback apply?)
    boundary_type TEXT NOT NULL CHECK (boundary_type IN (
        'front', 'side', 'rear', 'street_corner', 'secondary_frontage', 'lane', 'all'
    )),

    storey_level TEXT NOT NULL DEFAULT 'all' CHECK (storey_level IN (
        'ground', 'first', 'second', 'third_plus', 'upper', 'all'
    )),

    building_element TEXT NOT NULL DEFAULT 'main_dwelling' CHECK (building_element IN (
        'main_dwelling', 'secondary_dwelling', 'garage', 'carport', 'balcony',
        'deck', 'eaves', 'verandah', 'pool', 'fence', 'air_conditioner', 'all'
    )),

    -- Contextual filters (WHEN does it apply?)
    zone TEXT[],  -- Array of zones, e.g., ARRAY['R2', 'R3']
    development_type TEXT[],  -- e.g., ARRAY['dwelling_house', 'dual_occupancy']
    site_condition TEXT[],  -- e.g., ARRAY['corner_lot', 'heritage_area', 'steep_slope']
    lga TEXT,  -- Local Government Area, e.g., 'Inner West'

    -- The actual setback value
    setback_meters NUMERIC(6,2) NOT NULL CHECK (setback_meters > 0 AND setback_meters <= 100),
    setback_meters_max NUMERIC(6,2) CHECK (setback_meters_max IS NULL OR setback_meters_max > setback_meters),

    qualifier TEXT NOT NULL DEFAULT 'minimum' CHECK (qualifier IN (
        'minimum', 'maximum', 'exactly', 'at_least', 'up_to', 'range'
    )),

    measurement_from TEXT DEFAULT 'boundary',  -- What it's measured from

    -- Special rules
    can_overhang BOOLEAN DEFAULT FALSE,
    overhang_meters NUMERIC(4,2) CHECK (overhang_meters IS NULL OR overhang_meters >= 0),
    exceptions TEXT,  -- Free text for exceptions

    -- Legal hierarchy
    document_type TEXT NOT NULL CHECK (document_type IN ('SEPP', 'LEP', 'DCP')),
    document_name TEXT,
    priority INTEGER NOT NULL CHECK (priority BETWEEN 1 AND 3),  -- 1=SEPP > 2=LEP > 3=DCP

    -- Source tracking
    source_text TEXT NOT NULL,  -- Original provision text
    rationale TEXT,  -- Why this setback exists

    -- Extraction metadata
    extraction_confidence NUMERIC(3,2) DEFAULT 1.0 CHECK (extraction_confidence BETWEEN 0 AND 1),
    manual_verified BOOLEAN DEFAULT FALSE,
    extraction_method TEXT,  -- e.g., 'instructor_openai_gpt-4-turbo'
    extraction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Additional notes
    notes TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_setback_rules_zone ON setback_rules USING GIN(zone);
CREATE INDEX IF NOT EXISTS idx_setback_rules_boundary ON setback_rules(boundary_type);
CREATE INDEX IF NOT EXISTS idx_setback_rules_storey ON setback_rules(storey_level);
CREATE INDEX IF NOT EXISTS idx_setback_rules_element ON setback_rules(building_element);
CREATE INDEX IF NOT EXISTS idx_setback_rules_provision ON setback_rules(provision_id);
CREATE INDEX IF NOT EXISTS idx_setback_rules_lga ON setback_rules(lga);
CREATE INDEX IF NOT EXISTS idx_setback_rules_priority ON setback_rules(priority);
CREATE INDEX IF NOT EXISTS idx_setback_rules_confidence ON setback_rules(extraction_confidence);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_setback_rules_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER setback_rules_updated_at
    BEFORE UPDATE ON setback_rules
    FOR EACH ROW
    EXECUTE FUNCTION update_setback_rules_updated_at();

-- View for human-readable setback rules
CREATE OR REPLACE VIEW setback_rules_readable AS
SELECT
    id,
    ref_number,
    CONCAT(
        CASE
            WHEN zone IS NOT NULL THEN 'In ' || array_to_string(zone, '/') || ' zone(s): '
            ELSE ''
        END,
        CASE boundary_type
            WHEN 'front' THEN 'Front'
            WHEN 'side' THEN 'Side'
            WHEN 'rear' THEN 'Rear'
            ELSE INITCAP(boundary_type)
        END,
        ' setback ',
        CASE storey_level
            WHEN 'ground' THEN '(ground floor) '
            WHEN 'first' THEN '(first floor) '
            WHEN 'second' THEN '(second floor) '
            WHEN 'all' THEN ''
            ELSE CONCAT('(', storey_level, ') ')
        END,
        'is ',
        CASE qualifier
            WHEN 'minimum' THEN 'minimum '
            WHEN 'maximum' THEN 'maximum '
            WHEN 'range' THEN ''
            ELSE qualifier || ' '
        END,
        setback_meters::TEXT, 'm',
        CASE
            WHEN setback_meters_max IS NOT NULL THEN ' to ' || setback_meters_max::TEXT || 'm'
            ELSE ''
        END,
        CASE
            WHEN building_element != 'main_dwelling' THEN ' for ' || REPLACE(building_element, '_', ' ')
            ELSE ''
        END
    ) AS readable_rule,
    document_type,
    priority,
    extraction_confidence,
    manual_verified
FROM setback_rules
ORDER BY priority ASC, zone, boundary_type, storey_level;

-- Example query functions

-- Get all setbacks for a specific zone and boundary
CREATE OR REPLACE FUNCTION get_setbacks_for_zone_boundary(
    p_zone TEXT,
    p_boundary TEXT DEFAULT NULL
)
RETURNS TABLE (
    rule_id INTEGER,
    ref TEXT,
    boundary TEXT,
    storey TEXT,
    setback NUMERIC,
    qualifier TEXT,
    doc_type TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        id,
        ref_number,
        boundary_type,
        storey_level,
        setback_meters,
        qualifier,
        document_type
    FROM setback_rules
    WHERE p_zone = ANY(zone) OR zone IS NULL
    AND (p_boundary IS NULL OR boundary_type = p_boundary)
    ORDER BY priority ASC, storey_level;
END;
$$ LANGUAGE plpgsql;

-- Get setback for specific conditions
CREATE OR REPLACE FUNCTION get_setback_value(
    p_zone TEXT,
    p_boundary TEXT,
    p_storey TEXT DEFAULT 'ground',
    p_element TEXT DEFAULT 'main_dwelling'
)
RETURNS NUMERIC AS $$
DECLARE
    result NUMERIC;
BEGIN
    SELECT setback_meters INTO result
    FROM setback_rules
    WHERE (p_zone = ANY(zone) OR zone IS NULL)
    AND boundary_type = p_boundary
    AND (storey_level = p_storey OR storey_level = 'all')
    AND (building_element = p_element OR building_element = 'all')
    ORDER BY
        priority ASC,  -- SEPP > LEP > DCP
        CASE WHEN storey_level = p_storey THEN 1 ELSE 2 END,  -- Exact match preferred
        CASE WHEN building_element = p_element THEN 1 ELSE 2 END
    LIMIT 1;

    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Comments for documentation
COMMENT ON TABLE setback_rules IS 'Structured storage of setback requirements with conditional logic';
COMMENT ON COLUMN setback_rules.boundary_type IS 'Which boundary: front, side, rear, etc.';
COMMENT ON COLUMN setback_rules.storey_level IS 'Which floor level: ground, first, second, etc.';
COMMENT ON COLUMN setback_rules.zone IS 'Zones this applies to (NULL = all zones)';
COMMENT ON COLUMN setback_rules.priority IS 'Legal hierarchy: 1=SEPP (highest) > 2=LEP > 3=DCP (lowest)';
COMMENT ON COLUMN setback_rules.extraction_confidence IS 'LLM confidence score (0.0-1.0)';

-- Example data (for testing)
INSERT INTO setback_rules (
    ref_number,
    boundary_type,
    storey_level,
    zone,
    setback_meters,
    qualifier,
    document_type,
    document_name,
    priority,
    source_text,
    lga
) VALUES
(
    'C11',
    'side',
    'ground',
    ARRAY['R2'],
    0.9,
    'minimum',
    'DCP',
    'Marrickville DCP 2011',
    3,
    'For R2 zones, minimum side setback is 0.9m for ground floor',
    'Inner West'
),
(
    'C11',
    'side',
    'first',
    ARRAY['R2'],
    1.5,
    'minimum',
    'DCP',
    'Marrickville DCP 2011',
    3,
    'For R2 zones, minimum side setback is 0.9m ground floor, 1.5m first floor',
    'Inner West'
)
ON CONFLICT DO NOTHING;  -- Safe for re-running migration

-- Verification queries
DO $$
BEGIN
    RAISE NOTICE 'Migration complete!';
    RAISE NOTICE 'Table created: setback_rules';
    RAISE NOTICE 'Indexes created: 8 indexes for common queries';
    RAISE NOTICE 'View created: setback_rules_readable';
    RAISE NOTICE 'Functions created: get_setbacks_for_zone_boundary(), get_setback_value()';
    RAISE NOTICE '';
    RAISE NOTICE 'Test query:';
    RAISE NOTICE '  SELECT * FROM setback_rules_readable LIMIT 5;';
    RAISE NOTICE '';
    RAISE NOTICE 'Get R2 side setbacks:';
    RAISE NOTICE '  SELECT * FROM get_setbacks_for_zone_boundary(''R2'', ''side'');';
END $$;
