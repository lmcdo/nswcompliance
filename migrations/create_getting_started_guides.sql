-- Migration: Create getting_started_guides table
-- Purpose: Store step-by-step guides for common development scenarios
-- Date: 2026-01-20

-- Table: getting_started_guides
-- Stores comprehensive guides for common development projects
CREATE TABLE IF NOT EXISTS getting_started_guides (
  id SERIAL PRIMARY KEY,

  -- Guide identification
  guide_id VARCHAR(10) NOT NULL UNIQUE,           -- G1, G2, etc.
  title TEXT NOT NULL,                            -- "I Want to Build a Granny Flat"
  slug VARCHAR(100) NOT NULL UNIQUE,              -- "build-granny-flat"

  -- Target audience
  target_user TEXT NOT NULL,                      -- "Homeowner with existing dwelling"

  -- Overview estimates
  typical_timeline TEXT,                          -- "3-6 months"
  typical_cost_range TEXT,                        -- "$80,000-150,000 + $5,000-15,000 approvals"

  -- Eligibility criteria (JSON)
  eligibility JSONB,                              -- {"min_lot_size": "450sqm", "zones": ["R2", "R3"]}

  -- Step-by-step process (JSON array)
  steps JSONB NOT NULL,                           -- Array of step objects

  -- Common pitfalls to avoid (JSON array)
  common_pitfalls JSONB,                          -- Array of pitfall descriptions

  -- Related content
  related_qa_ids TEXT[],                          -- ["Q1", "Q2", "Q3"]
  related_checklist_ids TEXT[],                   -- ["CL3"]

  -- Source
  source_document TEXT,
  source_url TEXT,
  last_verified DATE,

  -- Display order
  display_order INTEGER DEFAULT 0,
  is_published BOOLEAN DEFAULT true,

  -- Metadata
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for getting_started_guides
CREATE INDEX IF NOT EXISTS idx_getting_started_guides_slug
  ON getting_started_guides(slug);

CREATE INDEX IF NOT EXISTS idx_getting_started_guides_published
  ON getting_started_guides(is_published, display_order);

CREATE INDEX IF NOT EXISTS idx_getting_started_guides_fts
  ON getting_started_guides
  USING GIN(to_tsvector('english', title || ' ' || target_user));

-- Comments
COMMENT ON TABLE getting_started_guides IS 'Step-by-step guides for common development scenarios like granny flats, second storeys, etc.';
COMMENT ON COLUMN getting_started_guides.guide_id IS 'Short unique identifier (G1, G2, etc.)';
COMMENT ON COLUMN getting_started_guides.steps IS 'JSON array of step objects with step_number, title, description, duration, tasks, tips';
COMMENT ON COLUMN getting_started_guides.eligibility IS 'JSON object with eligibility criteria like min_lot_size, zones, existing_dwelling';
