-- PRP-8B: Authoritative Schema Creation
-- Creates parallel authoritative schema for NSW Planning Portal integration

-- Create authoritative schema
CREATE SCHEMA IF NOT EXISTS authoritative;

-- 1. NSW PLANNING PORTAL PROPERTY DATA
CREATE TABLE IF NOT EXISTS authoritative.nsw_properties (
    property_id BIGINT PRIMARY KEY, -- NSW Portal property ID
    address TEXT NOT NULL,
    lot_dp TEXT, -- Lot/DP reference
    
    -- Planning controls from NSW Portal
    zone_code VARCHAR(10) NOT NULL,
    lga_name VARCHAR(100) NOT NULL,
    lep_name VARCHAR(200) NOT NULL,
    height_limit DECIMAL(5,2),
    height_units VARCHAR(10) DEFAULT 'm',
    fsr_limit DECIMAL(4,2),
    
    -- Additional planning layers
    heritage_status VARCHAR(100),
    heritage_item_number VARCHAR(50),
    acid_sulfate_class INTEGER,
    flood_planning_level DECIMAL(6,2),
    bushfire_prone BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    data_source VARCHAR(50) DEFAULT 'NSW_PLANNING_PORTAL',
    last_synced TIMESTAMP DEFAULT NOW(),
    sync_status VARCHAR(20) DEFAULT 'current',
    
    -- Spatial data (if available)
    lot_geometry JSONB,
    
    CONSTRAINT valid_zone CHECK (zone_code ~ '^[A-Z][0-9]?[0-9]?$')
);

-- 2. AUTHORITATIVE PROVISIONS WITH HIERARCHY
CREATE TABLE IF NOT EXISTS authoritative.planning_provisions (
    id SERIAL PRIMARY KEY,
    
    -- Document identification
    document_type VARCHAR(10) NOT NULL, -- 'SEPP', 'LEP', 'DCP'
    document_name VARCHAR(200) NOT NULL,
    clause_reference VARCHAR(100) NOT NULL,
    
    -- Hierarchy and precedence
    authority_level INTEGER NOT NULL, -- 1=SEPP, 2=LEP, 3=DCP
    precedence_score DECIMAL(5,2) DEFAULT 50.00, -- Within same level
    
    -- Provision content
    provision_text TEXT NOT NULL,
    provision_type VARCHAR(50) NOT NULL, -- 'setback', 'height', 'fsr', 'heritage'
    
    -- Applicability
    applicable_zones VARCHAR[] NOT NULL, -- ['R1', 'R2', 'R3']
    applicable_lgas VARCHAR[], -- ['INNER_WEST', 'CANTERBURY_BANKSTOWN']
    applicable_dev_types VARCHAR[], -- ['dwelling_house', 'dual_occupancy']
    
    -- Extracted measurements (nullable for qualitative)
    numeric_value DECIMAL(8,2),
    unit VARCHAR(10),
    measurement_context VARCHAR(100), -- 'minimum', 'maximum', 'standard'
    boundary_type VARCHAR(50), -- 'front', 'rear', 'side'
    
    -- Conditions and variations
    conditions JSONB, -- {"heritage_area": true, "corner_lot": false}
    
    -- JSON preservation from original extraction
    original_json JSONB, -- Full AutoSchemaKG/LangExtract output
    semantic_relationships JSONB, -- Entity-relation mappings
    
    -- Verification and confidence
    extraction_method VARCHAR(50) NOT NULL, -- 'langextract', 'manual', 'api'
    extraction_confidence DECIMAL(3,2) NOT NULL DEFAULT 0.85,
    verification_status VARCHAR(50) DEFAULT 'pending',
    verified_by VARCHAR(100),
    verified_date TIMESTAMP,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_current BOOLEAN DEFAULT TRUE,
    superseded_by INTEGER REFERENCES authoritative.planning_provisions(id),
    
    UNIQUE(document_name, clause_reference, boundary_type, applicable_dev_types)
);

-- 3. AUTHORITY TIER CLASSIFICATION
CREATE TABLE IF NOT EXISTS authoritative.provision_authority_tiers (
    provision_id INTEGER REFERENCES authoritative.planning_provisions(id),
    tier_level INTEGER NOT NULL, -- 1-5 based on our tier system
    tier_name VARCHAR(50) NOT NULL, -- 'fully_authoritative', 'high_authority', etc.
    confidence_level DECIMAL(3,2) NOT NULL, -- 0.60 to 1.00
    professional_required BOOLEAN DEFAULT FALSE,
    specialist_type VARCHAR(100), -- 'heritage_consultant', 'traffic_engineer'
    
    PRIMARY KEY(provision_id)
);

-- 4. PROPERTY-PROVISION MATCHING WITH CONFIDENCE
CREATE TABLE IF NOT EXISTS authoritative.property_provision_analysis (
    id SERIAL PRIMARY KEY,
    property_id BIGINT REFERENCES authoritative.nsw_properties(property_id),
    provision_id INTEGER REFERENCES authoritative.planning_provisions(id),
    
    -- Applicability scoring
    applicability_score DECIMAL(3,2) NOT NULL, -- 0.00 to 1.00
    applicability_reason TEXT,
    
    -- Hierarchy resolution
    is_primary_authority BOOLEAN DEFAULT FALSE, -- Highest in hierarchy for this requirement
    superseded_by_provision INTEGER REFERENCES authoritative.planning_provisions(id),
    
    -- Context matching
    context_match JSONB, -- {"heritage": true, "zone_match": true}
    
    -- Professional notes
    interpretation_required BOOLEAN DEFAULT FALSE,
    professional_guidance TEXT,
    
    -- Metadata
    analysis_date TIMESTAMP DEFAULT NOW(),
    analysis_version VARCHAR(20) DEFAULT 'v1.0',
    
    CONSTRAINT unique_property_provision UNIQUE(property_id, provision_id)
);

-- 5. HIERARCHY RESOLUTION CACHE
CREATE TABLE IF NOT EXISTS authoritative.hierarchy_resolution_cache (
    id SERIAL PRIMARY KEY,
    cache_key VARCHAR(500) NOT NULL, -- zone:dev_type:requirement_type:boundary
    
    -- Resolution result
    primary_provision_id INTEGER REFERENCES authoritative.planning_provisions(id),
    authority_chain JSONB, -- Array of all applicable provisions in hierarchy order
    
    -- Resolution metadata
    resolution_method VARCHAR(50), -- 'sepp_override', 'most_restrictive', 'lep_standard'
    resolution_confidence DECIMAL(3,2),
    
    -- Cache management
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP DEFAULT (NOW() + INTERVAL '7 days'),
    hit_count INTEGER DEFAULT 0,
    
    UNIQUE(cache_key)
);

-- 6. PROFESSIONAL GUIDANCE TEMPLATES
CREATE TABLE IF NOT EXISTS authoritative.professional_guidance (
    id SERIAL PRIMARY KEY,
    scenario_type VARCHAR(100) NOT NULL, -- 'heritage_overlay', 'complex_subdivision'
    
    -- Guidance content
    guidance_text TEXT NOT NULL,
    complexity_level VARCHAR(20), -- 'low', 'medium', 'high', 'extreme'
    
    -- Professional requirements
    specialists_required VARCHAR[],
    typical_timeline VARCHAR(100),
    estimated_cost_range VARCHAR(100),
    
    -- Next steps
    recommended_actions JSONB, -- Ordered list of actions
    council_contacts JSONB,
    
    -- Applicability
    applicable_zones VARCHAR[],
    applicable_scenarios JSONB,
    
    is_current BOOLEAN DEFAULT TRUE
);

-- 7. VISUAL GUIDANCE AND EXAMPLES
CREATE TABLE IF NOT EXISTS authoritative.compliance_visual_aids (
    id SERIAL PRIMARY KEY,
    provision_id INTEGER REFERENCES authoritative.planning_provisions(id),
    
    -- Visual content
    visual_type VARCHAR(50) NOT NULL, -- 'technical_diagram', 'site_photo', 'compliance_example'
    image_url VARCHAR(500),
    image_description TEXT,
    
    -- Interactive elements
    annotations JSONB, -- Hotspots, measurements, callouts
    
    -- Context
    example_property_zone VARCHAR(10),
    compliance_status VARCHAR(20), -- 'compliant', 'non_compliant', 'variation'
    
    -- Metadata
    created_by VARCHAR(100),
    verified_by_professional BOOLEAN DEFAULT FALSE,
    display_priority INTEGER DEFAULT 100
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_nsw_properties_zone ON authoritative.nsw_properties(zone_code);
CREATE INDEX IF NOT EXISTS idx_nsw_properties_lga ON authoritative.nsw_properties(lga_name);
CREATE INDEX IF NOT EXISTS idx_provisions_zones ON authoritative.planning_provisions USING GIN(applicable_zones);
CREATE INDEX IF NOT EXISTS idx_provisions_type ON authoritative.planning_provisions(provision_type);
CREATE INDEX IF NOT EXISTS idx_provisions_authority ON authoritative.planning_provisions(authority_level);
CREATE INDEX IF NOT EXISTS idx_property_analysis ON authoritative.property_provision_analysis(property_id, is_primary_authority);
CREATE INDEX IF NOT EXISTS idx_cache_key ON authoritative.hierarchy_resolution_cache(cache_key);
CREATE INDEX IF NOT EXISTS idx_cache_expiry ON authoritative.hierarchy_resolution_cache(expires_at);

-- Grant permissions
GRANT USAGE ON SCHEMA authoritative TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA authoritative TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA authoritative TO postgres;

COMMENT ON SCHEMA authoritative IS 'PRP-8B: Authoritative compliance system with NSW Planning Portal integration';