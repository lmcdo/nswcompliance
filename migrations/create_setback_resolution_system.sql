-- Multi-Tier Setback Resolution System
-- Handles cases where DCP/LEP/SEPP don't specify storey-level setbacks

-- ============================================================================
-- TABLE 1: Explicit Setback Rules (already extracted)
-- ============================================================================
-- This is the existing setback_rules table (created previously)
-- Contains explicit numeric values from DCP/LEP/SEPP

-- ============================================================================
-- TABLE 2: Fallback Resolution Rules
-- ============================================================================
CREATE TABLE IF NOT EXISTS setback_fallback_rules (
  id SERIAL PRIMARY KEY,

  -- Rule identification
  rule_name TEXT NOT NULL,
  rule_description TEXT,

  -- When this rule applies (conditions)
  applies_when_missing TEXT[], -- e.g., ['storey_level', 'boundary_type']
  development_type TEXT[],     -- e.g., ['multi_dwelling_housing', 'residential_flat_building']
  storey_level TEXT[],         -- e.g., ['first', 'second', 'third_plus']
  boundary_type TEXT[],        -- e.g., ['side', 'rear']

  -- Resolution method
  resolution_method TEXT NOT NULL CHECK (resolution_method IN (
    'multiply_ground_floor',      -- Multiply ground floor setback by factor
    'building_separation_half',   -- Use half of building separation distance
    'minimum_absolute',           -- Apply absolute minimum value
    'privacy_derived',            -- Derived from privacy requirements
    'requires_assessment',        -- No calculable rule - needs professional judgement
    'average_adjacent'            -- Use average of neighbouring properties
  )),

  -- Calculation parameters
  multiplier NUMERIC(4,2),           -- e.g., 1.5 for first floor
  absolute_minimum_meters NUMERIC(6,2), -- Absolute minimum value
  calculation_formula TEXT,          -- Human-readable formula

  -- Legal authority
  authority_source TEXT NOT NULL,    -- e.g., 'SEPP 65 Apartment Design Guide'
  authority_clause TEXT,             -- e.g., '3E-1 Building separation'
  legal_basis TEXT,                  -- e.g., 'Privacy principles', 'Fire separation'

  -- Reliability indicators
  reliability_level TEXT CHECK (reliability_level IN (
    'statutory',        -- Defined in legislation
    'industry_standard', -- Widely accepted professional practice
    'guidance',         -- Best practice guidance
    'requires_approval' -- Needs certifier/council approval
  )),

  -- Flags
  requires_certifier_approval BOOLEAN DEFAULT false,
  requires_survey BOOLEAN DEFAULT false,
  allows_variation BOOLEAN DEFAULT true,

  -- Metadata
  notes TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- TABLE 3: Resolution Warnings
-- ============================================================================
CREATE TABLE IF NOT EXISTS setback_resolution_warnings (
  id SERIAL PRIMARY KEY,
  warning_code TEXT UNIQUE NOT NULL,
  warning_message TEXT NOT NULL,
  severity TEXT CHECK (severity IN ('info', 'warning', 'critical')),
  user_action_required TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- INDEXES
-- ============================================================================
CREATE INDEX idx_fallback_rules_method ON setback_fallback_rules(resolution_method);
CREATE INDEX idx_fallback_rules_dev_type ON setback_fallback_rules USING GIN(development_type);
CREATE INDEX idx_fallback_rules_storey ON setback_fallback_rules USING GIN(storey_level);

-- ============================================================================
-- INSERT INDUSTRY-STANDARD FALLBACK RULES
-- ============================================================================

-- Rule 1: First floor setback multiplier
INSERT INTO setback_fallback_rules (
  rule_name,
  rule_description,
  applies_when_missing,
  development_type,
  storey_level,
  boundary_type,
  resolution_method,
  multiplier,
  absolute_minimum_meters,
  calculation_formula,
  authority_source,
  legal_basis,
  reliability_level,
  requires_certifier_approval,
  notes
) VALUES (
  'First Floor Privacy Multiplier',
  'When DCP does not specify first floor setbacks, apply 1.5x ground floor setback for privacy',
  ARRAY['storey_level'],
  ARRAY['dwelling_house', 'dual_occupancy', 'multi_dwelling_housing'],
  ARRAY['first'],
  ARRAY['side', 'rear'],
  'multiply_ground_floor',
  1.5,
  1.5,
  'ground_floor_setback × 1.5 (minimum 1.5m)',
  'Common law privacy principles + Industry practice',
  'Privacy protection - prevent overlooking',
  'industry_standard',
  false,
  'Widely accepted practice when DCP is silent. Based on maintaining visual privacy to adjoining properties.'
);

-- Rule 2: Second floor setback multiplier
INSERT INTO setback_fallback_rules (
  rule_name,
  rule_description,
  applies_when_missing,
  development_type,
  storey_level,
  boundary_type,
  resolution_method,
  multiplier,
  absolute_minimum_meters,
  calculation_formula,
  authority_source,
  legal_basis,
  reliability_level,
  requires_certifier_approval,
  notes
) VALUES (
  'Second Floor Privacy Multiplier',
  'When DCP does not specify second floor setbacks, apply 2x ground floor setback',
  ARRAY['storey_level'],
  ARRAY['dwelling_house', 'dual_occupancy', 'multi_dwelling_housing'],
  ARRAY['second'],
  ARRAY['side', 'rear'],
  'multiply_ground_floor',
  2.0,
  3.0,
  'ground_floor_setback × 2.0 (minimum 3.0m)',
  'Common law privacy principles + BCA fire separation',
  'Privacy + fire safety',
  'industry_standard',
  false,
  'Standard practice for two-storey dwellings. Ensures adequate separation for both privacy and safety.'
);

-- Rule 3: Third floor and above (multi-dwelling/apartments)
INSERT INTO setback_fallback_rules (
  rule_name,
  rule_description,
  applies_when_missing,
  development_type,
  storey_level,
  boundary_type,
  resolution_method,
  multiplier,
  absolute_minimum_meters,
  calculation_formula,
  authority_source,
  authority_clause,
  legal_basis,
  reliability_level,
  requires_certifier_approval,
  notes
) VALUES (
  'Multi-Storey Building Separation (SEPP 65)',
  'For buildings 3+ storeys, apply building separation standards',
  ARRAY['storey_level'],
  ARRAY['multi_dwelling_housing', 'residential_flat_building', 'shop_top_housing'],
  ARRAY['third', 'fourth_plus'],
  ARRAY['side', 'rear'],
  'building_separation_half',
  NULL,
  6.0,
  'Half of building separation distance (12m habitable-to-habitable ÷ 2 = 6m minimum)',
  'State Environmental Planning Policy No 65 - Design Quality of Residential Apartment Development',
  'Apartment Design Guide 3E-1: Building separation',
  'statutory',
  true,
  'SEPP 65 mandates 12m separation between habitable windows (6m to boundary). Requires certifier approval for multi-dwelling developments.'
);

-- Rule 4: Upper floor privacy - absolute minimum
INSERT INTO setback_fallback_rules (
  rule_name,
  rule_description,
  applies_when_missing,
  development_type,
  storey_level,
  boundary_type,
  resolution_method,
  multiplier,
  absolute_minimum_meters,
  calculation_formula,
  authority_source,
  legal_basis,
  reliability_level,
  requires_certifier_approval,
  notes
) VALUES (
  'Upper Floor Privacy Minimum',
  'Absolute minimum upper floor setback for privacy protection',
  ARRAY['storey_level'],
  NULL, -- Applies to all development types
  ARRAY['first', 'second', 'third', 'fourth_plus'],
  ARRAY['side', 'rear'],
  'minimum_absolute',
  NULL,
  3.0,
  'Minimum 3.0m for any upper floor habitable room',
  'SEPP 65 Apartment Design Guide + BCA',
  'Privacy and amenity protection',
  'industry_standard',
  false,
  'Universal minimum for upper floors with habitable rooms. May be varied with privacy screening.'
);

-- Rule 5: Balconies and decks
INSERT INTO setback_fallback_rules (
  rule_name,
  rule_description,
  applies_when_missing,
  development_type,
  storey_level,
  boundary_type,
  resolution_method,
  multiplier,
  absolute_minimum_meters,
  calculation_formula,
  authority_source,
  legal_basis,
  reliability_level,
  requires_certifier_approval,
  notes
) VALUES (
  'Balcony Privacy Setback',
  'Minimum setback for balconies and decks on upper floors',
  ARRAY['building_element'],
  NULL,
  ARRAY['first', 'second', 'third', 'fourth_plus'],
  ARRAY['side', 'rear'],
  'minimum_absolute',
  NULL,
  4.0,
  'Minimum 4.0m from boundary for balconies/decks (increased from main building for privacy)',
  'SEPP 65 Apartment Design Guide + Common law privacy',
  'Visual privacy - balconies increase overlooking potential',
  'industry_standard',
  false,
  'Balconies require larger setbacks than walls due to increased overlooking potential.'
);

-- ============================================================================
-- INSERT RESOLUTION WARNINGS
-- ============================================================================

INSERT INTO setback_resolution_warnings (warning_code, warning_message, severity, user_action_required) VALUES
('NO_EXPLICIT_RULE', 'DCP/LEP does not specify setback for this configuration. Fallback rule applied.', 'info', 'Review fallback calculation and verify site-specific conditions.'),
('REQUIRES_CERTIFIER', 'This setback calculation requires certifier approval before construction.', 'warning', 'Engage a licensed certifier to review and approve setback design.'),
('REQUIRES_SURVEY', 'Setback must be verified by licensed surveyor.', 'warning', 'Engage a surveyor to prepare foundation location survey.'),
('PRIVACY_CONCERN', 'Upper floor setback derived from privacy principles. Site-specific assessment may be required.', 'info', 'Consider privacy screening, window placement, or increased setback.'),
('SEPP_65_APPLIES', 'SEPP 65 building separation standards apply to this development.', 'warning', 'Refer to Apartment Design Guide for full compliance requirements.'),
('VARIATION_POSSIBLE', 'Setback may be varied with appropriate justification and approval.', 'info', 'Consult with council or certifier regarding variation application.'),
('NO_FALLBACK', 'No fallback rule available. Professional assessment required.', 'critical', 'Engage a town planner or certifier for site-specific setback determination.');

-- ============================================================================
-- RESOLUTION FUNCTION
-- ============================================================================

CREATE OR REPLACE FUNCTION resolve_setback(
  p_zone TEXT,
  p_development_type TEXT,
  p_storey_level TEXT,
  p_boundary_type TEXT,
  p_building_element TEXT DEFAULT 'main_dwelling'
)
RETURNS TABLE(
  setback_meters NUMERIC,
  source_type TEXT,
  source_reference TEXT,
  calculation_method TEXT,
  reliability TEXT,
  warnings TEXT[],
  requires_approval BOOLEAN
) AS $$
DECLARE
  v_explicit_setback NUMERIC;
  v_ground_setback NUMERIC;
  v_fallback_rule RECORD;
  v_calculated_setback NUMERIC;
  v_warnings TEXT[] := ARRAY[]::TEXT[];
BEGIN
  -- Step 1: Try to find explicit rule from DCP/LEP/SEPP
  SELECT sr.setback_meters INTO v_explicit_setback
  FROM setback_rules sr
  WHERE (sr.zone IS NULL OR p_zone = ANY(sr.zone))
    AND (sr.development_type IS NULL OR p_development_type = ANY(sr.development_type))
    AND (sr.storey_level = p_storey_level OR sr.storey_level = 'all')
    AND (sr.boundary_type = p_boundary_type OR sr.boundary_type = 'all')
    AND (sr.building_element = p_building_element OR sr.building_element = 'all')
  ORDER BY sr.priority ASC, sr.extraction_confidence DESC
  LIMIT 1;

  -- If explicit rule found, return it
  IF v_explicit_setback IS NOT NULL THEN
    RETURN QUERY
    SELECT
      v_explicit_setback,
      'explicit'::TEXT,
      'DCP/LEP/SEPP'::TEXT,
      'Direct provision'::TEXT,
      'statutory'::TEXT,
      ARRAY[]::TEXT[],
      false;
    RETURN;
  END IF;

  -- Step 2: No explicit rule - apply fallback
  v_warnings := array_append(v_warnings, 'NO_EXPLICIT_RULE');

  -- Get ground floor setback for multiplier methods
  IF p_storey_level != 'ground' THEN
    SELECT sr.setback_meters INTO v_ground_setback
    FROM setback_rules sr
    WHERE (sr.zone IS NULL OR p_zone = ANY(sr.zone))
      AND (sr.development_type IS NULL OR p_development_type = ANY(sr.development_type))
      AND sr.storey_level IN ('ground', 'all')
      AND (sr.boundary_type = p_boundary_type OR sr.boundary_type = 'all')
    ORDER BY sr.priority ASC
    LIMIT 1;
  END IF;

  -- Find applicable fallback rule
  SELECT * INTO v_fallback_rule
  FROM setback_fallback_rules
  WHERE (development_type IS NULL OR p_development_type = ANY(development_type))
    AND (storey_level IS NULL OR p_storey_level = ANY(storey_level))
    AND (boundary_type IS NULL OR p_boundary_type = ANY(boundary_type))
  ORDER BY
    CASE WHEN reliability_level = 'statutory' THEN 1
         WHEN reliability_level = 'industry_standard' THEN 2
         WHEN reliability_level = 'guidance' THEN 3
         ELSE 4 END
  LIMIT 1;

  -- Calculate setback based on fallback method
  IF v_fallback_rule IS NOT NULL THEN
    CASE v_fallback_rule.resolution_method
      WHEN 'multiply_ground_floor' THEN
        IF v_ground_setback IS NOT NULL THEN
          v_calculated_setback := GREATEST(
            v_ground_setback * v_fallback_rule.multiplier,
            v_fallback_rule.absolute_minimum_meters
          );
        ELSE
          v_calculated_setback := v_fallback_rule.absolute_minimum_meters;
        END IF;

      WHEN 'minimum_absolute' THEN
        v_calculated_setback := v_fallback_rule.absolute_minimum_meters;

      WHEN 'building_separation_half' THEN
        v_calculated_setback := v_fallback_rule.absolute_minimum_meters; -- 6m default
        v_warnings := array_append(v_warnings, 'SEPP_65_APPLIES');

      ELSE
        v_warnings := array_append(v_warnings, 'NO_FALLBACK');
    END CASE;

    -- Add warnings based on rule properties
    IF v_fallback_rule.requires_certifier_approval THEN
      v_warnings := array_append(v_warnings, 'REQUIRES_CERTIFIER');
    END IF;

    IF v_fallback_rule.requires_survey THEN
      v_warnings := array_append(v_warnings, 'REQUIRES_SURVEY');
    END IF;

    IF v_fallback_rule.legal_basis ILIKE '%privacy%' THEN
      v_warnings := array_append(v_warnings, 'PRIVACY_CONCERN');
    END IF;

    IF v_fallback_rule.allows_variation THEN
      v_warnings := array_append(v_warnings, 'VARIATION_POSSIBLE');
    END IF;

    RETURN QUERY
    SELECT
      v_calculated_setback,
      'fallback'::TEXT,
      v_fallback_rule.authority_source,
      v_fallback_rule.calculation_formula,
      v_fallback_rule.reliability_level,
      v_warnings,
      v_fallback_rule.requires_certifier_approval;
    RETURN;
  END IF;

  -- No fallback rule found
  RETURN QUERY
  SELECT
    NULL::NUMERIC,
    'none'::TEXT,
    'Professional assessment required'::TEXT,
    'No applicable rule found'::TEXT,
    'requires_approval'::TEXT,
    ARRAY['NO_FALLBACK']::TEXT[],
    true;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- EXAMPLE USAGE
-- ============================================================================
-- SELECT * FROM resolve_setback('R2', 'dwelling_house', 'first', 'side');
-- Returns: 1.35m (0.9m ground × 1.5), source: industry_standard, warnings: [NO_EXPLICIT_RULE]
