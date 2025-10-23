-- LightRAG Categorization Schema
-- Purpose: Store AI-categorized requirements from DCP provisions
-- Date: 2025-10-23
-- Phase: Week 2 - Processing & Validation

-- ============================================================================
-- Table 1: DCP Base Requirements
-- ============================================================================
-- Purpose: Store generic requirements that apply to all properties in an
--          LGA/Zone/DevType combination (e.g., "R2 Dwelling House in Marrickville")
-- Example: "Front setback: 5.5m" applies to ALL R2 dwelling houses in Marrickville

CREATE TABLE IF NOT EXISTS dcp_base_requirements (
    id SERIAL PRIMARY KEY,

    -- Scope identifiers (what properties does this apply to?)
    lga TEXT NOT NULL,                      -- 'Inner West', 'Marrickville', etc.
    zone TEXT,                              -- 'R2', 'B1', NULL = applies to all zones
    development_type TEXT,                  -- 'dwelling_house', NULL = applies to all types

    -- Categorization
    category TEXT NOT NULL,                 -- 'setback_front', 'parking', 'landscaping', etc.
    subcategory TEXT,                       -- Optional: 'front', 'side', 'rear' for setbacks

    -- Requirement content
    requirement_text TEXT NOT NULL,         -- Human-readable: "Front setback: 5.5m"
    value_numeric NUMERIC,                  -- Extracted value: 5.5
    value_min NUMERIC,                      -- For ranges: "5.5m to 6m"
    value_max NUMERIC,
    unit TEXT,                              -- 'm', '%', 'spaces', etc.

    -- Provenance (critical for compliance)
    source_provision_ids INTEGER[],         -- Links to regulatory_provisions.id
    source_document_ids TEXT[],             -- Document IDs for quick reference
    pdf_pages INTEGER[],                    -- PDF page numbers
    extraction_context JSONB,               -- LLM reasoning, tables extracted, etc.

    -- Quality assurance
    confidence TEXT CHECK (confidence IN ('high', 'medium', 'low')),
    confidence_score NUMERIC,               -- 0.0 to 1.0
    has_conditionals BOOLEAN DEFAULT FALSE, -- "except", "however", "unless"
    conditional_text TEXT,                  -- Store the conditional clause

    -- Validation status
    validated BOOLEAN DEFAULT FALSE,
    validated_by TEXT,
    validated_at TIMESTAMP,
    validation_notes TEXT,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    processing_version TEXT,                -- Track which LLM/prompt version

    -- Indexes for fast querying
    UNIQUE(lga, zone, development_type, category, subcategory)
);

-- Indexes for base requirements
CREATE INDEX idx_dcp_base_lga_zone_devtype ON dcp_base_requirements(lga, zone, development_type);
CREATE INDEX idx_dcp_base_category ON dcp_base_requirements(category);
CREATE INDEX idx_dcp_base_validated ON dcp_base_requirements(validated);
CREATE INDEX idx_dcp_base_confidence ON dcp_base_requirements(confidence);

-- ============================================================================
-- Table 2: DCP Precinct Requirements
-- ============================================================================
-- Purpose: Store precinct-specific supplements/overrides
-- Example: "Abergeldie Estate: Maintain low-density character" only applies
--          to properties in that specific precinct

CREATE TABLE IF NOT EXISTS dcp_precinct_requirements (
    id SERIAL PRIMARY KEY,

    -- Scope identifiers
    precinct_id TEXT NOT NULL,              -- Links to dcp_precinct_provisions.precinct_id
    precinct_name TEXT,                     -- Human-readable name
    lga TEXT NOT NULL,

    -- Categorization
    category TEXT NOT NULL,
    subcategory TEXT,

    -- Requirement content
    requirement_text TEXT NOT NULL,
    value_numeric NUMERIC,
    value_min NUMERIC,
    value_max NUMERIC,
    unit TEXT,

    -- Relationship to base requirements
    overrides_base_requirement_id INTEGER REFERENCES dcp_base_requirements(id),
    supplements_base BOOLEAN DEFAULT TRUE,  -- TRUE = adds to base, FALSE = replaces base

    -- Provenance
    source_provision_ids INTEGER[],
    source_document_ids TEXT[],
    pdf_pages INTEGER[],
    extraction_context JSONB,

    -- Quality assurance
    confidence TEXT CHECK (confidence IN ('high', 'medium', 'low')),
    confidence_score NUMERIC,
    has_conditionals BOOLEAN DEFAULT FALSE,
    conditional_text TEXT,

    -- Validation status
    validated BOOLEAN DEFAULT FALSE,
    validated_by TEXT,
    validated_at TIMESTAMP,
    validation_notes TEXT,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    processing_version TEXT,

    -- Indexes
    UNIQUE(precinct_id, category, subcategory, requirement_text)
);

-- Indexes for precinct requirements
CREATE INDEX idx_dcp_precinct_id ON dcp_precinct_requirements(precinct_id);
CREATE INDEX idx_dcp_precinct_lga ON dcp_precinct_requirements(lga);
CREATE INDEX idx_dcp_precinct_category ON dcp_precinct_requirements(category);
CREATE INDEX idx_dcp_precinct_validated ON dcp_precinct_requirements(validated);

-- ============================================================================
-- Table 3: Categorization Validation
-- ============================================================================
-- Purpose: Track expert validation of LLM categorization
-- Used to calculate precision/recall metrics and improve categorization

CREATE TABLE IF NOT EXISTS categorization_validation (
    id SERIAL PRIMARY KEY,

    -- What provision was categorized?
    provision_id INTEGER REFERENCES regulatory_provisions(id),
    provision_text TEXT,
    document_id TEXT,

    -- LLM categorization
    llm_category TEXT,
    llm_subcategory TEXT,
    llm_confidence TEXT,
    llm_reasoning TEXT,                     -- Why did LLM choose this category?

    -- Expert validation
    expert_category TEXT,                   -- What category should it actually be?
    expert_subcategory TEXT,
    validation_status TEXT CHECK (validation_status IN (
        'correct',                          -- LLM got it right
        'false_positive',                   -- LLM categorized, shouldn't have
        'false_negative',                   -- LLM missed it
        'wrong_category',                   -- LLM categorized but wrong category
        'needs_review'                      -- Uncertain, needs second opinion
    )),

    -- Expert feedback
    expert_notes TEXT,
    correction_applied BOOLEAN DEFAULT FALSE,

    -- Metadata
    expert_reviewed_by TEXT,
    expert_reviewed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for validation
CREATE INDEX idx_validation_provision ON categorization_validation(provision_id);
CREATE INDEX idx_validation_status ON categorization_validation(validation_status);
CREATE INDEX idx_validation_llm_category ON categorization_validation(llm_category);
CREATE INDEX idx_validation_expert_category ON categorization_validation(expert_category);

-- ============================================================================
-- Table 4: Category Definitions
-- ============================================================================
-- Purpose: Define valid categories and their validation keywords
-- Used for automated validation (keyword cross-check)

CREATE TABLE IF NOT EXISTS requirement_categories (
    id SERIAL PRIMARY KEY,
    category TEXT UNIQUE NOT NULL,
    subcategories TEXT[],                   -- Valid subcategories
    display_name TEXT,                      -- UI-friendly name
    description TEXT,

    -- Validation keywords (for automated recall check)
    positive_keywords TEXT[],               -- Words that indicate this category
    negative_keywords TEXT[],               -- Words that indicate NOT this category

    -- Metrics thresholds
    min_recall_threshold NUMERIC DEFAULT 0.90,
    min_precision_threshold NUMERIC DEFAULT 0.95,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert default categories
INSERT INTO requirement_categories (category, display_name, positive_keywords, min_recall_threshold, min_precision_threshold)
VALUES
    ('setback_front', 'Front Setback', ARRAY['front', 'setback', 'frontage', 'street'], 0.90, 0.95),
    ('setback_side', 'Side Setback', ARRAY['side', 'setback', 'lateral'], 0.90, 0.95),
    ('setback_rear', 'Rear Setback', ARRAY['rear', 'setback', 'back'], 0.90, 0.95),
    ('parking', 'Parking', ARRAY['parking', 'car', 'vehicle', 'space'], 0.90, 0.95),
    ('landscaping', 'Landscaping', ARRAY['landscape', 'garden', 'planting', 'tree'], 0.85, 0.90),
    ('building_height', 'Building Height', ARRAY['height', 'storey', 'floor'], 0.90, 0.95),
    ('site_coverage', 'Site Coverage', ARRAY['coverage', 'footprint', 'site area'], 0.85, 0.90),
    ('character', 'Character', ARRAY['character', 'heritage', 'appearance'], 0.80, 0.85),
    ('privacy', 'Privacy', ARRAY['privacy', 'overlooking', 'screening'], 0.85, 0.90),
    ('fencing', 'Fencing', ARRAY['fence', 'fencing', 'boundary'], 0.85, 0.90)
ON CONFLICT (category) DO NOTHING;

-- ============================================================================
-- Views for Easy Querying
-- ============================================================================

-- View: All requirements for an address (combines base + precinct)
CREATE OR REPLACE VIEW v_requirements_by_address AS
SELECT
    'base' as requirement_type,
    lga,
    zone,
    development_type,
    NULL as precinct_id,
    category,
    subcategory,
    requirement_text,
    value_numeric,
    unit,
    source_provision_ids,
    confidence,
    validated
FROM dcp_base_requirements
UNION ALL
SELECT
    'precinct' as requirement_type,
    lga,
    NULL as zone,
    NULL as development_type,
    precinct_id,
    category,
    subcategory,
    requirement_text,
    value_numeric,
    unit,
    source_provision_ids,
    confidence,
    validated
FROM dcp_precinct_requirements;

-- View: Validation metrics by category
CREATE OR REPLACE VIEW v_validation_metrics AS
SELECT
    llm_category,
    COUNT(*) as total_validations,
    SUM(CASE WHEN validation_status = 'correct' THEN 1 ELSE 0 END) as correct,
    SUM(CASE WHEN validation_status = 'false_positive' THEN 1 ELSE 0 END) as false_positives,
    SUM(CASE WHEN validation_status = 'false_negative' THEN 1 ELSE 0 END) as false_negatives,
    SUM(CASE WHEN validation_status = 'wrong_category' THEN 1 ELSE 0 END) as wrong_category,
    ROUND(
        SUM(CASE WHEN validation_status = 'correct' THEN 1 ELSE 0 END)::NUMERIC /
        NULLIF(COUNT(*), 0) * 100,
        2
    ) as accuracy_percent
FROM categorization_validation
WHERE validation_status IS NOT NULL
GROUP BY llm_category;

-- ============================================================================
-- Comments for Documentation
-- ============================================================================

COMMENT ON TABLE dcp_base_requirements IS 'LightRAG-categorized base requirements that apply to all properties in an LGA/Zone/DevType combination';
COMMENT ON TABLE dcp_precinct_requirements IS 'LightRAG-categorized precinct-specific requirements that supplement or override base requirements';
COMMENT ON TABLE categorization_validation IS 'Expert validation of LLM categorization for quality assurance';
COMMENT ON TABLE requirement_categories IS 'Category definitions and validation thresholds';

-- ============================================================================
-- Grants (adjust as needed for your database users)
-- ============================================================================

-- Grant SELECT to application users (read-only)
-- GRANT SELECT ON dcp_base_requirements TO app_user;
-- GRANT SELECT ON dcp_precinct_requirements TO app_user;
-- GRANT SELECT ON v_requirements_by_address TO app_user;

-- Grant INSERT/UPDATE for processing scripts
-- GRANT INSERT, UPDATE ON dcp_base_requirements TO processing_user;
-- GRANT INSERT, UPDATE ON dcp_precinct_requirements TO processing_user;
-- GRANT INSERT, UPDATE ON categorization_validation TO processing_user;

-- ============================================================================
-- Schema Creation Complete
-- ============================================================================

SELECT 'LightRAG categorization schema created successfully' as status;
