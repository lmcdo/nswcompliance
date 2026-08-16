-- DCP Version Management Schema
-- Enables point-in-time compliance assessment for DAs lodged before DCP amendments
--
-- Usage:
-- 1. When a DCP amendment occurs, record it in dcp_amendments
-- 2. Close out affected provisions by setting effective_until
-- 3. Import new provisions with effective_from = amendment date
-- 4. Query provisions using lodgement date for historical assessments

-- ============================================================================
-- STEP 1: Add version tracking columns to regulatory_provisions
-- ============================================================================

-- Add effective date columns for provision-level version tracking
ALTER TABLE regulatory_provisions
ADD COLUMN IF NOT EXISTS effective_from DATE DEFAULT '2020-01-01';

ALTER TABLE regulatory_provisions
ADD COLUMN IF NOT EXISTS effective_until DATE DEFAULT NULL;

ALTER TABLE regulatory_provisions
ADD COLUMN IF NOT EXISTS amendment_reference TEXT;

COMMENT ON COLUMN regulatory_provisions.effective_from IS
  'Date when this provision became active. NULL or early date = original provision.';

COMMENT ON COLUMN regulatory_provisions.effective_until IS
  'Date when this provision was superseded. NULL = still current.';

COMMENT ON COLUMN regulatory_provisions.amendment_reference IS
  'Reference to the amendment that introduced or superseded this provision (e.g., "Amendment 15 - TOD Parking")';

-- Create index for efficient point-in-time queries
CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_effective_dates
ON regulatory_provisions (lga, effective_from, effective_until);

-- ============================================================================
-- STEP 2: Create DCP amendments tracking table
-- ============================================================================

CREATE TABLE IF NOT EXISTS dcp_amendments (
  id SERIAL PRIMARY KEY,
  lga TEXT NOT NULL,
  amendment_name TEXT NOT NULL,              -- "Amendment 15 - TOD Parking"
  amendment_number TEXT,                      -- "15" or "2024/1"
  effective_date DATE NOT NULL,
  gazette_date DATE,                          -- NSW Government Gazette publication date
  affected_chapters TEXT[],                   -- ['Chapter 2.5', 'Chapter 2.14']
  affected_document_ids TEXT[],               -- Specific document_ids affected
  summary TEXT,                               -- Brief description of changes
  source_pdf_url TEXT,                        -- URL to amendment PDF
  source_pdf_path TEXT,                       -- Local path to downloaded PDF
  provisions_affected_count INT DEFAULT 0,   -- Number of provisions changed
  provisions_added_count INT DEFAULT 0,       -- New provisions added
  provisions_removed_count INT DEFAULT 0,     -- Provisions made obsolete
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  created_by TEXT,                            -- User who recorded the amendment
  notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_dcp_amendments_lga
ON dcp_amendments (lga, effective_date);

CREATE INDEX IF NOT EXISTS idx_dcp_amendments_affected_chapters
ON dcp_amendments USING GIN (affected_chapters);

COMMENT ON TABLE dcp_amendments IS
  'Changelog of DCP amendments. Used to track when provisions changed and enable point-in-time queries.';

-- ============================================================================
-- STEP 3: Create LGA registry table (optional but recommended)
-- ============================================================================

CREATE TABLE IF NOT EXISTS lga_registry (
  id SERIAL PRIMARY KEY,
  lga_code TEXT UNIQUE NOT NULL,              -- "parramatta", "central_coast"
  lga_name TEXT NOT NULL,                     -- "City of Parramatta"
  parent_lga TEXT,                            -- For merged councils (e.g., "Inner West")
  former_councils TEXT[],                     -- ['Gosford', 'Wyong']
  config_json JSONB,                          -- Full CouncilConfig as JSON
  dcp_citation TEXT,                          -- "Central Coast DCP 2022"
  dcp_adoption_date DATE,                     -- When DCP was adopted
  dcp_latest_amendment DATE,                  -- Date of most recent amendment
  total_provisions INT DEFAULT 0,
  total_precincts INT DEFAULT 0,
  status TEXT DEFAULT 'active',               -- 'active', 'planned', 'archived'
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lga_registry_status
ON lga_registry (status);

COMMENT ON TABLE lga_registry IS
  'Registry of LGAs supported by the compliance engine. Stores config and metadata.';

-- ============================================================================
-- STEP 4: Helper functions for point-in-time queries
-- ============================================================================

-- Function to get provisions that applied on a specific date
CREATE OR REPLACE FUNCTION get_provisions_at_date(
  p_lga TEXT,
  p_date DATE
)
RETURNS TABLE (
  id INT,
  document_id TEXT,
  provision_text TEXT,
  v2_dcp_layer TEXT,
  v2_dcp_part TEXT,
  v2_topic TEXT,
  v2_provision_type TEXT,
  effective_from DATE,
  effective_until DATE,
  amendment_reference TEXT
)
LANGUAGE SQL
STABLE
AS $$
  SELECT
    id,
    document_id,
    provision_text,
    v2_dcp_layer,
    v2_dcp_part,
    v2_topic,
    v2_provision_type,
    effective_from,
    effective_until,
    amendment_reference
  FROM regulatory_provisions
  WHERE lga = p_lga
    AND effective_from <= p_date
    AND (effective_until IS NULL OR effective_until > p_date);
$$;

COMMENT ON FUNCTION get_provisions_at_date IS
  'Returns provisions that were active on a specific date. Use for DAs lodged before amendments.';

-- Function to get provisions affected by an amendment
CREATE OR REPLACE FUNCTION get_provisions_affected_by_amendment(
  p_amendment_id INT
)
RETURNS TABLE (
  id INT,
  document_id TEXT,
  provision_text TEXT,
  change_type TEXT  -- 'added', 'removed', 'modified'
)
LANGUAGE SQL
STABLE
AS $$
  WITH amendment AS (
    SELECT amendment_name, effective_date, lga, affected_document_ids
    FROM dcp_amendments
    WHERE id = p_amendment_id
  )
  SELECT
    p.id,
    p.document_id,
    p.provision_text,
    CASE
      WHEN p.effective_from = a.effective_date THEN 'added'
      WHEN p.effective_until = a.effective_date - INTERVAL '1 day' THEN 'removed'
      ELSE 'modified'
    END as change_type
  FROM regulatory_provisions p
  CROSS JOIN amendment a
  WHERE p.lga = a.lga
    AND p.amendment_reference = a.amendment_name;
$$;

-- ============================================================================
-- STEP 5: Sample data for testing
-- ============================================================================

-- Example: Insert a sample amendment record
-- INSERT INTO dcp_amendments (lga, amendment_name, effective_date, affected_chapters, summary)
-- VALUES (
--   'Central Coast',
--   'TOD Parking Amendment',
--   '2025-05-09',
--   ARRAY['Chapter 2.5', 'Chapter 2.14'],
--   'Updated parking rates for Transit-Oriented Development areas'
-- );

-- Example: Close out old provisions when amendment takes effect
-- UPDATE regulatory_provisions
-- SET effective_until = '2025-05-08',
--     updated_at = NOW()
-- WHERE lga = 'Central Coast'
--   AND document_id LIKE '%Chapter_2.5%'
--   AND effective_until IS NULL;

-- ============================================================================
-- STEP 6: Views for common queries
-- ============================================================================

-- View: Current provisions only (excludes superseded)
CREATE OR REPLACE VIEW v_current_provisions AS
SELECT *
FROM regulatory_provisions
WHERE effective_until IS NULL;

COMMENT ON VIEW v_current_provisions IS
  'Shows only currently active provisions (not superseded by amendments).';

-- View: Amendment history by LGA
CREATE OR REPLACE VIEW v_amendment_history AS
SELECT
  lga,
  amendment_name,
  effective_date,
  affected_chapters,
  provisions_affected_count,
  provisions_added_count,
  provisions_removed_count,
  summary
FROM dcp_amendments
ORDER BY lga, effective_date DESC;

COMMENT ON VIEW v_amendment_history IS
  'Shows amendment history sorted by LGA and date.';

-- ============================================================================
-- Migration notes
-- ============================================================================
--
-- To apply this schema to existing data:
-- 1. Run this script to add columns and create tables
-- 2. Set effective_from = '2020-01-01' for all existing provisions (already done via DEFAULT)
-- 3. When an amendment occurs:
--    a. INSERT into dcp_amendments
--    b. UPDATE old provisions with effective_until = day before amendment
--    c. INSERT new provisions with effective_from = amendment date
--
-- For Inner West existing data, all provisions are assumed current unless
-- an amendment is recorded.
