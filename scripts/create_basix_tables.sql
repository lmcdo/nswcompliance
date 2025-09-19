-- BASIX and Special Provisions Database Schema
-- PRP-Q1 and PRP-Q2 Implementation

-- Drop existing tables if they exist
DROP TABLE IF EXISTS basix_provisions CASCADE;
DROP TABLE IF EXISTS special_provisions_registry CASCADE;
DROP TABLE IF EXISTS provision_thresholds CASCADE;
DROP TABLE IF EXISTS provision_implications CASCADE;

-- =====================================================
-- BASIX PROVISIONS TABLE (PRP-Q1)
-- =====================================================
CREATE TABLE basix_provisions (
    id SERIAL PRIMARY KEY,
    climate_zone VARCHAR(50) NOT NULL,
    development_type VARCHAR(100) NOT NULL,

    -- Energy targets
    energy_reduction_target DECIMAL(5,2),  -- Percentage
    thermal_comfort_rating DECIMAL(3,1),   -- Star rating

    -- Water targets
    water_reduction_target DECIMAL(5,2),   -- Percentage
    water_fixture_rating INTEGER,          -- WELS rating

    -- Compliance thresholds
    min_insulation_r_value DECIMAL(3,1),
    max_glazing_percentage DECIMAL(5,2),

    -- Metadata
    effective_date DATE DEFAULT CURRENT_DATE,
    source_document VARCHAR(255) DEFAULT 'BASIX SEPP 2004',
    tier_level INTEGER DEFAULT 1,  -- BASIX is Tier 1 (fully authoritative)

    UNIQUE(climate_zone, development_type)
);

-- Populate with NSW BASIX requirements for Inner West zones
INSERT INTO basix_provisions (climate_zone, development_type, energy_reduction_target, water_reduction_target, thermal_comfort_rating) VALUES
-- Zone 17 (Ashfield, Lewisham area)
('Zone 17', 'dwelling_house', 40.0, 40.0, 5.0),
('Zone 17', 'residential_flat_building', 35.0, 40.0, 4.5),
('Zone 17', 'dual_occupancy', 40.0, 40.0, 5.0),
('Zone 17', 'multi_dwelling_housing', 35.0, 40.0, 4.5),
('Zone 17', 'shop_top_housing', 35.0, 40.0, 4.5),

-- Zone 18 (Marrickville, Stanmore area)
('Zone 18', 'dwelling_house', 45.0, 40.0, 5.5),
('Zone 18', 'residential_flat_building', 40.0, 40.0, 5.0),
('Zone 18', 'dual_occupancy', 45.0, 40.0, 5.5),
('Zone 18', 'multi_dwelling_housing', 40.0, 40.0, 5.0),
('Zone 18', 'shop_top_housing', 40.0, 40.0, 5.0),

-- Generic zones for other areas
('Zone 19', 'dwelling_house', 45.0, 40.0, 5.5),
('Zone 19', 'residential_flat_building', 40.0, 40.0, 5.0),
('Zone 20', 'dwelling_house', 50.0, 40.0, 6.0),
('Zone 20', 'residential_flat_building', 45.0, 40.0, 5.5);

-- =====================================================
-- SPECIAL PROVISIONS REGISTRY (PRP-Q2)
-- =====================================================
CREATE TABLE special_provisions_registry (
    id SERIAL PRIMARY KEY,
    provision_type VARCHAR(100) NOT NULL,
    provision_category VARCHAR(100),
    provision_subtype VARCHAR(100),

    -- Hierarchy placement
    default_tier_level INTEGER NOT NULL CHECK (default_tier_level BETWEEN 1 AND 5),
    authority_level INTEGER NOT NULL CHECK (authority_level BETWEEN 0 AND 100),

    -- Processing rules
    requires_specialist BOOLEAN DEFAULT FALSE,
    has_numeric_thresholds BOOLEAN DEFAULT FALSE,
    affects_development_types TEXT[], -- Array of affected development types

    -- Metadata
    legislation_reference VARCHAR(255),
    last_updated DATE DEFAULT CURRENT_DATE,
    active BOOLEAN DEFAULT TRUE,

    UNIQUE(provision_type, provision_category, provision_subtype)
);

-- Populate special provisions registry
INSERT INTO special_provisions_registry
(provision_type, provision_category, default_tier_level, authority_level, requires_specialist, has_numeric_thresholds, legislation_reference)
VALUES
-- Tier 1 - Fully Authoritative (Numeric requirements)
('Climate Zones', 'BASIX', 1, 100, FALSE, TRUE, 'BASIX SEPP 2004'),
('Flood Planning', 'Natural Hazards', 1, 95, TRUE, TRUE, 'SEPP (Resilience and Hazards) 2021'),
('Bushfire Prone Land', 'Natural Hazards', 1, 95, TRUE, TRUE, 'Planning for Bush Fire Protection 2019'),
('State Environmental Planning Policy', 'SEPP', 1, 95, FALSE, TRUE, 'Various SEPPs'),

-- Tier 2 - High Authority (Clear requirements)
('Acid Sulfate Soils', 'Environmental', 2, 85, TRUE, FALSE, 'LEP Clause 6.1'),
('Heritage', 'Conservation', 2, 90, TRUE, FALSE, 'LEP Clause 5.10'),
('Coastal Management', 'Environmental', 2, 90, TRUE, TRUE, 'SEPP (Resilience and Hazards) 2021'),
('Riparian Land', 'Environmental', 2, 85, FALSE, TRUE, 'Water Management Act 2000'),

-- Tier 3 - Moderate Authority (Qualitative)
('Biodiversity', 'Environmental', 3, 75, TRUE, FALSE, 'Biodiversity Conservation Act 2016'),
('Tree Preservation', 'Environmental', 3, 70, FALSE, FALSE, 'DCP Tree Management'),
('Contaminated Land', 'Environmental', 3, 80, TRUE, FALSE, 'SEPP (Resilience and Hazards) 2021'),

-- Tier 4 - Framework Guidance
('Urban Design', 'Design', 4, 60, FALSE, FALSE, 'DCP Urban Design Guidelines'),
('Sustainability', 'Environmental', 4, 65, FALSE, FALSE, 'DCP Sustainability Guidelines');

-- =====================================================
-- PROVISION THRESHOLDS TABLE
-- =====================================================
CREATE TABLE provision_thresholds (
    id SERIAL PRIMARY KEY,
    provision_id INTEGER REFERENCES special_provisions_registry(id) ON DELETE CASCADE,

    threshold_type VARCHAR(100), -- 'minimum', 'maximum', 'exact'
    measurement_context VARCHAR(100),
    numeric_value DECIMAL(10,2),
    unit VARCHAR(50),

    applies_to_zones TEXT[], -- Specific zones or NULL for all
    applies_to_dev_types TEXT[], -- Specific dev types or NULL for all

    UNIQUE(provision_id, threshold_type, measurement_context)
);

-- Flood planning thresholds
INSERT INTO provision_thresholds
(provision_id, threshold_type, measurement_context, numeric_value, unit)
VALUES
-- Flood planning requirements
((SELECT id FROM special_provisions_registry WHERE provision_type = 'Flood Planning'),
 'minimum', 'floor_level_above_flood', 0.5, 'm'),
((SELECT id FROM special_provisions_registry WHERE provision_type = 'Flood Planning'),
 'minimum', 'freeboard', 0.5, 'm'),
((SELECT id FROM special_provisions_registry WHERE provision_type = 'Flood Planning'),
 'minimum', 'flood_compatible_materials', 1.0, 'boolean'),

-- Bushfire requirements (BAL ratings)
((SELECT id FROM special_provisions_registry WHERE provision_type = 'Bushfire Prone Land'),
 'minimum', 'bushfire_attack_level', 12.5, 'BAL'),
((SELECT id FROM special_provisions_registry WHERE provision_type = 'Bushfire Prone Land'),
 'minimum', 'asset_protection_zone', 10.0, 'm'),

-- Riparian setbacks
((SELECT id FROM special_provisions_registry WHERE provision_type = 'Riparian Land'),
 'minimum', 'riparian_setback', 20.0, 'm'),
((SELECT id FROM special_provisions_registry WHERE provision_type = 'Riparian Land'),
 'minimum', 'vegetated_buffer', 10.0, 'm');

-- =====================================================
-- PROVISION IMPLICATIONS TABLE
-- =====================================================
CREATE TABLE provision_implications (
    id SERIAL PRIMARY KEY,
    provision_id INTEGER REFERENCES special_provisions_registry(id) ON DELETE CASCADE,

    implication_type VARCHAR(50), -- 'requirement', 'prohibition', 'assessment'
    implication_text TEXT,
    action_required TEXT,

    tier_level INTEGER,
    confidence_level DECIMAL(3,2)
);

-- Add implications for key provisions
INSERT INTO provision_implications
(provision_id, implication_type, implication_text, action_required, tier_level, confidence_level)
VALUES
-- BASIX implications
((SELECT id FROM special_provisions_registry WHERE provision_type = 'Climate Zones'),
 'requirement', 'BASIX Certificate required for all new residential development',
 'Submit BASIX Certificate with DA', 1, 1.0),

-- Flood implications
((SELECT id FROM special_provisions_registry WHERE provision_type = 'Flood Planning'),
 'assessment', 'Flood Impact Assessment required for development in flood prone land',
 'Engage qualified flood engineer', 1, 0.95),
((SELECT id FROM special_provisions_registry WHERE provision_type = 'Flood Planning'),
 'requirement', 'Minimum floor levels 500mm above 1:100 year flood level',
 'Design floor levels to comply', 1, 0.95),

-- Bushfire implications
((SELECT id FROM special_provisions_registry WHERE provision_type = 'Bushfire Prone Land'),
 'assessment', 'Bushfire Assessment Report required',
 'Engage bushfire consultant', 1, 0.95),
((SELECT id FROM special_provisions_registry WHERE provision_type = 'Bushfire Prone Land'),
 'requirement', 'Construction to AS3959 Bushfire Standard',
 'Design to appropriate BAL rating', 1, 0.95),

-- Heritage implications
((SELECT id FROM special_provisions_registry WHERE provision_type = 'Heritage'),
 'assessment', 'Heritage Impact Statement required',
 'Engage heritage consultant', 2, 0.90),
((SELECT id FROM special_provisions_registry WHERE provision_type = 'Heritage'),
 'requirement', 'Maintain heritage significance of item',
 'Design sympathetic to heritage values', 2, 0.90),

-- Acid Sulfate Soils implications
((SELECT id FROM special_provisions_registry WHERE provision_type = 'Acid Sulfate Soils'),
 'assessment', 'Acid Sulfate Soils Management Plan may be required',
 'Check excavation depth triggers', 2, 0.85),
((SELECT id FROM special_provisions_registry WHERE provision_type = 'Acid Sulfate Soils'),
 'requirement', 'Comply with Acid Sulfate Soils Management requirements',
 'Prepare ASSMP if triggered', 2, 0.85);

-- Create indexes for performance
CREATE INDEX idx_basix_zone_type ON basix_provisions(climate_zone, development_type);
CREATE INDEX idx_provisions_type ON special_provisions_registry(provision_type);
CREATE INDEX idx_provisions_active ON special_provisions_registry(active) WHERE active = TRUE;
CREATE INDEX idx_thresholds_provision ON provision_thresholds(provision_id);
CREATE INDEX idx_implications_provision ON provision_implications(provision_id);

-- Add comments for documentation
COMMENT ON TABLE basix_provisions IS 'BASIX requirements by climate zone and development type (PRP-Q1)';
COMMENT ON TABLE special_provisions_registry IS 'Registry of all special provisions with tier assignments (PRP-Q2)';
COMMENT ON TABLE provision_thresholds IS 'Numeric thresholds for provisions that have measurable requirements';
COMMENT ON TABLE provision_implications IS 'Implications and required actions for each provision type';

-- Verification query
SELECT
    'BASIX Provisions' as table_name,
    COUNT(*) as records
FROM basix_provisions
UNION ALL
SELECT
    'Special Provisions Registry',
    COUNT(*)
FROM special_provisions_registry
UNION ALL
SELECT
    'Provision Thresholds',
    COUNT(*)
FROM provision_thresholds
UNION ALL
SELECT
    'Provision Implications',
    COUNT(*)
FROM provision_implications;