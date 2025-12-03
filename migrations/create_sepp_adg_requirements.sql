-- Migration: Create sepp_adg_requirements table
-- Purpose: Store structured Design Criteria from NSW Apartment Design Guide
-- Source: ADG Parts 3 & 4 (March 2023)
-- Date: 2025-12-03

CREATE TABLE IF NOT EXISTS sepp_adg_requirements (
  id SERIAL PRIMARY KEY,

  -- Section identification
  section_code VARCHAR(10) NOT NULL,        -- '3D', '3E', '3F', '4A', etc.
  section_name VARCHAR(100) NOT NULL,       -- 'Solar and Daylight Access'

  -- Criteria identification
  criteria_number INTEGER,                   -- 1, 2, 3 within section
  criteria_id VARCHAR(20) NOT NULL UNIQUE,  -- '4A-1', '4A-2', '3F-1'

  -- Requirement content
  requirement_type VARCHAR(20) NOT NULL,    -- 'design_criteria', 'objective', 'design_guidance'
  requirement_text TEXT NOT NULL,           -- Full text of the requirement
  requirement_summary VARCHAR(200),         -- Concise summary for card display

  -- Numeric values (for Design Criteria)
  has_numeric_standard BOOLEAN DEFAULT false,
  numeric_value DECIMAL(10,2),              -- 70, 2, 12, 25, etc.
  numeric_unit VARCHAR(20),                 -- 'percent', 'hours', 'metres', 'sqm', 'cubic_m', 'units'
  numeric_comparator VARCHAR(10),           -- 'min', 'max', 'exactly'
  secondary_value DECIMAL(10,2),            -- For compound standards (e.g., 70% @ 2hrs)
  secondary_unit VARCHAR(20),

  -- Metric category for grouping/filtering
  metric_category VARCHAR(50),              -- 'solar_access', 'ventilation', 'separation', 'storage'

  -- Applicability
  applies_to TEXT[],                        -- ARRAY['apartments', 'balconies', 'common_areas']
  building_height_category VARCHAR(20),     -- 'up_to_12m', '12m_to_25m', 'over_25m', 'all'

  -- Source traceability
  source_pdf VARCHAR(100) NOT NULL,         -- 'apartment-design-guide-part-4.pdf'
  source_page INTEGER NOT NULL,             -- 85
  source_url TEXT,                          -- Full URL to PDF

  -- Legal authority
  legal_status VARCHAR(20) DEFAULT 'statutory',
  authority_reference VARCHAR(100) DEFAULT 'SEPP (Housing) 2021',

  -- Verification
  manual_verified BOOLEAN DEFAULT false,
  verified_by VARCHAR(100),
  verified_at TIMESTAMPTZ,

  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common query patterns
CREATE INDEX idx_adg_section ON sepp_adg_requirements(section_code);
CREATE INDEX idx_adg_metric ON sepp_adg_requirements(metric_category);
CREATE INDEX idx_adg_type ON sepp_adg_requirements(requirement_type);
CREATE INDEX idx_adg_numeric ON sepp_adg_requirements(has_numeric_standard) WHERE has_numeric_standard = true;
CREATE INDEX idx_adg_height ON sepp_adg_requirements(building_height_category);

-- Comment on table
COMMENT ON TABLE sepp_adg_requirements IS 'NSW Apartment Design Guide Design Criteria - statutory requirements for multi-dwelling developments under SEPP (Housing) 2021';
