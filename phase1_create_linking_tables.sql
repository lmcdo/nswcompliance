-- Phase 1: Create Linking Tables for Cross-References, Applicability, and Control Codes
-- Objective: Clean data structure for cross-reference resolution and zone applicability

-- ============================================================================
-- TABLE 1: cross_reference_index
-- Purpose: Store parsed cross-references from provision text for fast lookup
-- ============================================================================

CREATE TABLE IF NOT EXISTS cross_reference_index (
    id SERIAL PRIMARY KEY,
    source_provision_id INTEGER NOT NULL,  -- Provision containing the reference
    reference_type TEXT NOT NULL,          -- 'section', 'clause', 'figure', 'part', 'chapter', 'table'
    reference_number TEXT NOT NULL,        -- Extracted number (e.g., "8.3", "11.1c", "25.6")
    reference_text TEXT,                   -- Original text snippet (e.g., "Refer to Section 8.3")
    target_provision_id INTEGER,           -- Resolved target (may be NULL if unresolved)
    resolution_status TEXT DEFAULT 'unresolved',  -- 'resolved', 'unresolved', 'ambiguous'
    resolution_confidence REAL DEFAULT 0.0,       -- 0.0 to 1.0
    is_mandatory BOOLEAN DEFAULT FALSE,    -- true if "must comply", false if "see also"
    context_snippet TEXT,                  -- Surrounding text for context
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT fk_source_provision
        FOREIGN KEY (source_provision_id)
        REFERENCES regulatory_provisions(id)
        ON DELETE CASCADE
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_xref_source
    ON cross_reference_index(source_provision_id);

CREATE INDEX IF NOT EXISTS idx_xref_target
    ON cross_reference_index(target_provision_id)
    WHERE target_provision_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_xref_number
    ON cross_reference_index(reference_number);

CREATE INDEX IF NOT EXISTS idx_xref_type
    ON cross_reference_index(reference_type);

CREATE INDEX IF NOT EXISTS idx_xref_status
    ON cross_reference_index(resolution_status);

-- Composite index for common query pattern
CREATE INDEX IF NOT EXISTS idx_xref_type_number
    ON cross_reference_index(reference_type, reference_number);


-- ============================================================================
-- TABLE 2: provision_applicability
-- Purpose: Explicit zone applicability rules (handle NULL zones)
-- ============================================================================

CREATE TABLE IF NOT EXISTS provision_applicability (
    id SERIAL PRIMARY KEY,
    provision_id INTEGER NOT NULL,
    applies_to_zone TEXT,              -- Specific zone (R2, B4, etc.) or NULL for universal
    applies_to_all_zones BOOLEAN DEFAULT FALSE,
    applies_to_lga TEXT,               -- LGA name (e.g., 'Inner West', 'Canada Bay')
    applies_state_wide BOOLEAN DEFAULT FALSE,
    excluded_zones TEXT[],             -- Array of zones where provision does NOT apply
    applicability_source TEXT,         -- 'explicit_zone', 'text_mention', 'document_type', 'inferred'
    confidence_score REAL DEFAULT 1.0, -- 0.0 to 1.0
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT fk_provision_applicability
        FOREIGN KEY (provision_id)
        REFERENCES regulatory_provisions(id)
        ON DELETE CASCADE
);

-- Indexes for fast zone-based queries
CREATE INDEX IF NOT EXISTS idx_applicability_provision
    ON provision_applicability(provision_id);

CREATE INDEX IF NOT EXISTS idx_applicability_zone
    ON provision_applicability(applies_to_zone)
    WHERE applies_to_zone IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_applicability_all_zones
    ON provision_applicability(applies_to_all_zones)
    WHERE applies_to_all_zones = TRUE;

CREATE INDEX IF NOT EXISTS idx_applicability_state_wide
    ON provision_applicability(applies_state_wide)
    WHERE applies_state_wide = TRUE;

CREATE INDEX IF NOT EXISTS idx_applicability_lga
    ON provision_applicability(applies_to_lga);


-- ============================================================================
-- TABLE 3: control_codes
-- Purpose: Split multi-code provisions (C17, C18, C19) into individual records
-- ============================================================================

CREATE TABLE IF NOT EXISTS control_codes (
    id SERIAL PRIMARY KEY,
    code TEXT NOT NULL,                -- Individual code (e.g., 'C17', 'C18')
    provision_id INTEGER NOT NULL,     -- Links back to parent provision
    code_group TEXT,                   -- Display format (e.g., 'C17-C22')
    control_type TEXT,                 -- 'setback', 'height', 'fsr', 'parking', etc.
    sequence_number INTEGER,           -- Order within group (1, 2, 3...)
    is_range_start BOOLEAN DEFAULT FALSE,
    is_range_end BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT fk_control_code_provision
        FOREIGN KEY (provision_id)
        REFERENCES regulatory_provisions(id)
        ON DELETE CASCADE,

    -- Ensure each code-provision combination is unique
    CONSTRAINT unique_code_provision
        UNIQUE(code, provision_id)
);

-- Indexes for fast code lookups
CREATE INDEX IF NOT EXISTS idx_control_code
    ON control_codes(code);

CREATE INDEX IF NOT EXISTS idx_control_provision
    ON control_codes(provision_id);

CREATE INDEX IF NOT EXISTS idx_control_type
    ON control_codes(control_type);

CREATE INDEX IF NOT EXISTS idx_control_group
    ON control_codes(code_group);


-- ============================================================================
-- TABLE 4: provision_categories (Simplified from provision_type)
-- Purpose: Flatten complex provision types to simple display categories
-- ============================================================================

-- First, add new columns to regulatory_provisions (don't drop existing columns)
ALTER TABLE regulatory_provisions
ADD COLUMN IF NOT EXISTS provision_category TEXT;

ALTER TABLE regulatory_provisions
ADD COLUMN IF NOT EXISTS display_priority INTEGER DEFAULT 5;

ALTER TABLE regulatory_provisions
ADD COLUMN IF NOT EXISTS is_mandatory BOOLEAN DEFAULT TRUE;

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_provision_category
    ON regulatory_provisions(provision_category);

CREATE INDEX IF NOT EXISTS idx_provision_priority
    ON regulatory_provisions(display_priority);


-- ============================================================================
-- TABLE 5: provision_diagrams (For future visual element linking)
-- Purpose: Direct FK relationship between provisions and diagrams
-- ============================================================================

CREATE TABLE IF NOT EXISTS provision_diagrams (
    id SERIAL PRIMARY KEY,
    provision_id INTEGER NOT NULL,
    visual_element_id TEXT NOT NULL,   -- Links to visual_elements_real.id
    diagram_number TEXT,               -- Extracted figure number (e.g., "11.1b", "25.6")
    is_required BOOLEAN DEFAULT TRUE,  -- true if "must conform", false if "see also"
    link_method TEXT,                  -- 'page_proximity', 'figure_number', 'manual', 'section_header'
    confidence_score REAL DEFAULT 0.0,
    manually_verified BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT fk_provision_diagram
        FOREIGN KEY (provision_id)
        REFERENCES regulatory_provisions(id)
        ON DELETE CASCADE,

    -- Note: visual_elements_real.id is TEXT, so no FK constraint
    -- Will add after confirming visual element re-extraction format

    -- Ensure no duplicate links
    CONSTRAINT unique_provision_visual
        UNIQUE(provision_id, visual_element_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_provision_diagram_provision
    ON provision_diagrams(provision_id);

CREATE INDEX IF NOT EXISTS idx_provision_diagram_visual
    ON provision_diagrams(visual_element_id);

CREATE INDEX IF NOT EXISTS idx_provision_diagram_number
    ON provision_diagrams(diagram_number);


-- ============================================================================
-- VIEWS: Convenient query interfaces
-- ============================================================================

-- View 1: Provisions with resolved cross-references
CREATE OR REPLACE VIEW provisions_with_cross_refs AS
SELECT
    rp.id,
    rp.ref_number,
    rp.provision_text,
    rp.zone,
    rp.document_id,
    json_agg(
        json_build_object(
            'ref_type', xr.reference_type,
            'ref_number', xr.reference_number,
            'ref_text', xr.reference_text,
            'target_id', xr.target_provision_id,
            'is_mandatory', xr.is_mandatory,
            'status', xr.resolution_status
        )
    ) FILTER (WHERE xr.id IS NOT NULL) as cross_references
FROM regulatory_provisions rp
LEFT JOIN cross_reference_index xr ON rp.id = xr.source_provision_id
GROUP BY rp.id, rp.ref_number, rp.provision_text, rp.zone, rp.document_id;


-- View 2: Provisions with applicability context
CREATE OR REPLACE VIEW provisions_with_applicability AS
SELECT
    rp.id,
    rp.ref_number,
    rp.provision_text,
    rp.zone as explicit_zone,
    rp.document_id,
    pa.applies_to_zone,
    pa.applies_to_all_zones,
    pa.applies_state_wide,
    pa.applies_to_lga,
    pa.excluded_zones,
    pa.applicability_source,
    CASE
        WHEN rp.zone IS NOT NULL THEN 'explicit'
        WHEN pa.applies_state_wide THEN 'state_wide'
        WHEN pa.applies_to_all_zones THEN 'all_zones'
        WHEN pa.applies_to_zone IS NOT NULL THEN 'inferred_from_text'
        ELSE 'context_dependent'
    END as applicability_type
FROM regulatory_provisions rp
LEFT JOIN provision_applicability pa ON rp.id = pa.provision_id;


-- View 3: Consolidated control codes
CREATE OR REPLACE VIEW provisions_with_control_codes AS
SELECT
    rp.id,
    rp.ref_number,
    rp.provision_text,
    rp.zone,
    cc.code_group,
    array_agg(cc.code ORDER BY cc.sequence_number) as individual_codes,
    cc.control_type
FROM regulatory_provisions rp
LEFT JOIN control_codes cc ON rp.id = cc.provision_id
GROUP BY rp.id, rp.ref_number, rp.provision_text, rp.zone, cc.code_group, cc.control_type;


-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to update provision category based on provision_type
CREATE OR REPLACE FUNCTION update_provision_categories()
RETURNS INTEGER AS $$
DECLARE
    updated_count INTEGER := 0;
BEGIN
    -- Categorize provisions
    UPDATE regulatory_provisions
    SET
        provision_category = CASE provision_type
            WHEN 'relationship_overrides' THEN 'override'
            WHEN 'quantitative_standard' THEN 'numeric_control'
            WHEN 'permissibility' THEN 'use_permission'
            WHEN 'relationship_in_accordance_with' THEN 'diagram_requirement'
            WHEN 'relationship_subject_to' THEN 'conditional'
            WHEN 'relationship_refers_to' THEN 'cross_reference'
            ELSE 'general'
        END,
        display_priority = CASE provision_type
            WHEN 'relationship_overrides' THEN 1
            WHEN 'quantitative_standard' THEN 2
            WHEN 'permissibility' THEN 2
            WHEN 'relationship_in_accordance_with' THEN 3
            WHEN 'relationship_subject_to' THEN 4
            WHEN 'relationship_refers_to' THEN 5
            ELSE 6
        END,
        is_mandatory = CASE provision_type
            WHEN 'relationship_refers_to' THEN FALSE
            ELSE TRUE
        END
    WHERE provision_category IS NULL;

    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check table creation
DO $$
BEGIN
    RAISE NOTICE 'Tables created:';
    RAISE NOTICE '  cross_reference_index: %',
        (SELECT COUNT(*) FROM information_schema.tables
         WHERE table_name = 'cross_reference_index');
    RAISE NOTICE '  provision_applicability: %',
        (SELECT COUNT(*) FROM information_schema.tables
         WHERE table_name = 'provision_applicability');
    RAISE NOTICE '  control_codes: %',
        (SELECT COUNT(*) FROM information_schema.tables
         WHERE table_name = 'control_codes');
    RAISE NOTICE '  provision_diagrams: %',
        (SELECT COUNT(*) FROM information_schema.tables
         WHERE table_name = 'provision_diagrams');

    RAISE NOTICE 'New columns added to regulatory_provisions: provision_category, display_priority, is_mandatory';
    RAISE NOTICE 'Views created: provisions_with_cross_refs, provisions_with_applicability, provisions_with_control_codes';
END $$;
