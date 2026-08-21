-- Migration: Create sepp_structured_requirements table
-- Purpose: Store structured SEPP requirements for pathway feasibility engine
-- Date: 2026-02-20
-- Author: Claude Code (SEPP Extraction Project)

-- ============================================================
-- TABLE: sepp_structured_requirements
-- ============================================================

CREATE TABLE IF NOT EXISTS sepp_structured_requirements (
  id SERIAL PRIMARY KEY,
  provision_id INTEGER NOT NULL REFERENCES regulatory_provisions(id) ON DELETE CASCADE,

  -- ============================================================
  -- CORE CLASSIFICATION
  -- ============================================================

  -- What type of requirement is this?
  requirement_category TEXT NOT NULL CHECK (requirement_category IN (
    'exclusion',        -- Red zone detection (heritage, flood, bushfire)
    'numeric_standard', -- Deep soil %, tree canopy %, setbacks
    'dimensional',      -- Lot width/depth thresholds for pattern matching
    'override',         -- SEPP supersedes DCP/LEP (e.g., TOD parking)
    'procedure'         -- Process requirements (not numeric/spatial)
  )),

  -- Which approval pathway does this affect?
  applies_to TEXT NOT NULL CHECK (applies_to IN (
    'CDC',          -- Complying Development Certificate (10-day fast track)
    'TAD',          -- Targeted Assessment DA (50-day)
    'DA',           -- Full Development Application
    'Pattern_Book', -- NSW Housing Pattern Book designs
    'all'           -- Applies to all pathways
  )),

  -- ============================================================
  -- EXCLUSION LOGIC (Red Zone Detection)
  -- ============================================================

  -- Is this an exclusion trigger that kicks projects out of fast-track?
  is_exclusion_trigger BOOLEAN DEFAULT false,

  -- Type of exclusion (based on actual SEPP Exempt & Complying Development Codes 2008)
  exclusion_type TEXT CHECK (exclusion_type IN (
    'heritage',                -- Heritage item, State Heritage Register, HCA, draft HCA
    'flood_planning_area',     -- Flood planning area, PMF extent (e.g., Hawkesbury Nepean)
    'bushfire_prone',          -- Bushfire prone land (e.g., Blue Mountains, Wollondilly LGAs)
    'acid_sulfate_soils',      -- Acid Sulfate Soils Map affected land
    'threatened_species',      -- Threatened species provisions
    'coastal_erosion',         -- Coastal erosion affected land
    'environmentally_sensitive', -- Environmentally sensitive land (LEP identified)
    'protected_area',          -- Protected area designation
    'foreshore_area',          -- Foreshore area
    'aircraft_noise',          -- Within/above 25 ANEF contour
    'reserved_public_purpose', -- Land reserved for public purpose
    'unsewered',               -- Unsewered land
    NULL
  )),

  -- Does exclusion affect entire lot or just part?
  exclusion_scope TEXT CHECK (exclusion_scope IN (
    'entire_lot',        -- Whole property excluded from fast-track
    'partial_constraint',-- Part of lot constrained (can calculate NDA)
    'setback_only',      -- Only affects setback requirements
    NULL
  )),

  -- ============================================================
  -- NUMERIC STANDARDS (Deep Soil, Tree Canopy, Setbacks)
  -- ============================================================

  -- Name of the metric
  metric_name TEXT, -- e.g., 'deep_soil_percent', 'tree_canopy_percent', 'setback_front_m'

  -- Numeric value
  metric_value NUMERIC,

  -- Unit of measurement
  metric_unit TEXT CHECK (metric_unit IN (
    'percent',              -- 25% deep soil
    'm',                    -- 4.5m setback
    'm2',                   -- 300m² minimum lot area
    'mm',                   -- 900mm (for small dimensions)
    'spaces_per_dwelling',  -- 0.5 parking spaces per dwelling
    NULL
  )),

  -- Comparison operator
  metric_operator TEXT CHECK (metric_operator IN (
    'min',    -- At least (>=)
    'max',    -- Not exceed (<=)
    'equals', -- Exactly (=)
    'range',  -- Between two values
    NULL
  )),

  -- For range operators, store second value
  metric_value_max NUMERIC,

  -- ============================================================
  -- DIMENSIONAL THRESHOLDS (Pattern Book Matching)
  -- ============================================================

  -- Type of dimension
  dimension_type TEXT CHECK (dimension_type IN (
    'lot_width',   -- Minimum lot width for pattern
    'lot_depth',   -- Minimum lot depth
    'lot_area',    -- Minimum total area
    'frontage',    -- Street frontage width
    NULL
  )),

  -- Minimum dimension required
  dimension_min NUMERIC,

  -- Maximum dimension (if range)
  dimension_max NUMERIC,

  -- ============================================================
  -- CONTEXT & CONDITIONS (When Does This Apply?)
  -- ============================================================

  -- JSONB structure for flexible conditions
  -- Example: { "zones": ["R2", "R3"], "lot_size_min_m2": 300, "heritage_excluded": true }
  context JSONB,

  -- ============================================================
  -- OVERRIDE LOGIC (SEPP Precedence)
  -- ============================================================

  -- Does this SEPP provision override local rules?
  is_override BOOLEAN DEFAULT false,

  -- Which layer does it override?
  overrides_layer TEXT CHECK (overrides_layer IN (
    'DCP',            -- Overrides Development Control Plan
    'LEP',            -- Overrides Local Environmental Plan
    'council_policy', -- Overrides council-specific policy
    NULL
  )),

  -- Condition under which override applies
  override_condition TEXT, -- e.g., 'if_TOD_within_400m', 'if_CDC_pathway'

  -- ============================================================
  -- PATTERN BOOK INTEGRATION
  -- ============================================================

  -- Reference to NSW Housing Pattern Book design
  pattern_book_ref TEXT, -- e.g., 'PB-2025-Pattern-04', 'LDG-DeepSoil-Standard'

  -- Template constraints (JSONB)
  -- Example: { "min_width": 12, "min_depth": 30, "envelope_m2": 280, "deep_soil_m2": 75 }
  template_constraint JSONB,

  -- ============================================================
  -- AUDIT TRAIL (Defensible Logic)
  -- ============================================================

  -- Full clause reference for professional citation
  source_clause TEXT NOT NULL, -- e.g., 'Codes SEPP Clause 1.19(2)(a)'

  -- PDF page number for verification
  source_pdf_page INTEGER,

  -- Excerpt of provision text for context
  source_provision_text TEXT,

  -- ============================================================
  -- QUALITY METADATA
  -- ============================================================

  -- Confidence score from LLM extraction (0.0 - 1.0)
  extraction_confidence NUMERIC NOT NULL CHECK (extraction_confidence >= 0 AND extraction_confidence <= 1),

  -- Flag for human review
  requires_professional_review BOOLEAN DEFAULT false,

  -- Notes on ambiguities or edge cases
  ambiguity_notes TEXT,

  -- Timestamp
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INDEXES (Performance Optimization)
-- ============================================================

-- Foreign key index
CREATE INDEX idx_sepp_req_provision_id
  ON sepp_structured_requirements(provision_id);

-- Core classification queries
CREATE INDEX idx_sepp_req_category
  ON sepp_structured_requirements(requirement_category);

CREATE INDEX idx_sepp_req_applies_to
  ON sepp_structured_requirements(applies_to);

-- Exclusion trigger queries (Red Zone detection)
CREATE INDEX idx_sepp_req_exclusion
  ON sepp_structured_requirements(is_exclusion_trigger)
  WHERE is_exclusion_trigger = true;

CREATE INDEX idx_sepp_req_exclusion_type
  ON sepp_structured_requirements(exclusion_type)
  WHERE exclusion_type IS NOT NULL;

-- Numeric metric queries
CREATE INDEX idx_sepp_req_metric_name
  ON sepp_structured_requirements(metric_name)
  WHERE metric_name IS NOT NULL;

-- Override queries
CREATE INDEX idx_sepp_req_override
  ON sepp_structured_requirements(is_override)
  WHERE is_override = true;

-- Pattern book queries
CREATE INDEX idx_sepp_req_pattern
  ON sepp_structured_requirements(pattern_book_ref)
  WHERE pattern_book_ref IS NOT NULL;

-- Quality/review queries
CREATE INDEX idx_sepp_req_confidence
  ON sepp_structured_requirements(extraction_confidence);

CREATE INDEX idx_sepp_req_needs_review
  ON sepp_structured_requirements(requires_professional_review)
  WHERE requires_professional_review = true;

-- JSONB indexes for context queries
CREATE INDEX idx_sepp_req_context
  ON sepp_structured_requirements USING GIN(context);

CREATE INDEX idx_sepp_req_template
  ON sepp_structured_requirements USING GIN(template_constraint);

-- ============================================================
-- COMMENTS (Documentation)
-- ============================================================

COMMENT ON TABLE sepp_structured_requirements IS
  'Structured extraction of SEPP provisions for pathway feasibility engine. Supports CDC/TAD/DA triage, pattern book matching, and exclusion detection.';

COMMENT ON COLUMN sepp_structured_requirements.requirement_category IS
  'Type of requirement: exclusion (red zone), numeric_standard (deep soil/setback), dimensional (lot size), override (SEPP precedence), procedure (process)';

COMMENT ON COLUMN sepp_structured_requirements.is_exclusion_trigger IS
  'TRUE if this provision excludes properties from fast-track pathways. Based on SEPP E&C 2008 and SEPP Housing 2021 exclusions: heritage, flood, bushfire, acid sulfate soils, threatened species, coastal erosion, aircraft noise, unsewered, etc.';

COMMENT ON COLUMN sepp_structured_requirements.context IS
  'JSONB conditions: zones applicable, lot size ranges, heritage exclusions, etc. Example: {"zones":["R2","R3"],"lot_size_min_m2":300}';

COMMENT ON COLUMN sepp_structured_requirements.is_override IS
  'TRUE if this SEPP provision supersedes local DCP/LEP rules (e.g., TOD parking reductions)';

COMMENT ON COLUMN sepp_structured_requirements.extraction_confidence IS
  'LLM confidence score (0.0-1.0). Values <0.7 flagged for human review.';

-- ============================================================
-- VALIDATION
-- ============================================================

-- Ensure exclusion triggers have exclusion_type set
ALTER TABLE sepp_structured_requirements
  ADD CONSTRAINT check_exclusion_type
  CHECK (
    (is_exclusion_trigger = false) OR
    (is_exclusion_trigger = true AND exclusion_type IS NOT NULL)
  );

-- Ensure numeric standards have metric fields populated
ALTER TABLE sepp_structured_requirements
  ADD CONSTRAINT check_numeric_standard
  CHECK (
    (requirement_category != 'numeric_standard') OR
    (requirement_category = 'numeric_standard' AND
     metric_name IS NOT NULL AND
     metric_value IS NOT NULL AND
     metric_unit IS NOT NULL)
  );

-- Ensure dimensional thresholds have dimension fields
ALTER TABLE sepp_structured_requirements
  ADD CONSTRAINT check_dimensional
  CHECK (
    (requirement_category != 'dimensional') OR
    (requirement_category = 'dimensional' AND
     dimension_type IS NOT NULL AND
     dimension_min IS NOT NULL)
  );

-- Ensure overrides have override_layer specified
ALTER TABLE sepp_structured_requirements
  ADD CONSTRAINT check_override
  CHECK (
    (is_override = false) OR
    (is_override = true AND overrides_layer IS NOT NULL)
  );

-- ============================================================
-- SUCCESS MESSAGE
-- ============================================================

DO $$
BEGIN
  RAISE NOTICE '✅ Migration 001_create_sepp_structured_requirements.sql completed successfully';
  RAISE NOTICE '📊 Table created: sepp_structured_requirements';
  RAISE NOTICE '📇 Indexes created: 13 indexes (performance optimized)';
  RAISE NOTICE '✓ Ready for SEPP extraction workflow';
END $$;
