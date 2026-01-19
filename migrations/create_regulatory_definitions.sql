-- Migration: Create regulatory_definitions table
-- Purpose: Store structured definitions from DCP glossaries, SEPP Housing, and Standard Instrument LEP
-- Date: 2026-01-19

CREATE TABLE IF NOT EXISTS regulatory_definitions (
  id SERIAL PRIMARY KEY,

  -- Core definition fields
  term VARCHAR(200) NOT NULL,
  term_normalized VARCHAR(200) NOT NULL,  -- lowercase, stripped for matching
  definition_text TEXT NOT NULL,
  definition_summary VARCHAR(500),         -- AI-friendly short version (optional)

  -- Source citation
  source_document TEXT NOT NULL,           -- e.g., "Marrickville DCP 2011", "SEPP Housing 2021"
  source_clause VARCHAR(100),              -- e.g., "Schedule 10", "Chapter G"
  legislation_type VARCHAR(30) NOT NULL,   -- DCP, SEPP, SI_LEP
  lga VARCHAR(50),                         -- e.g., "Inner West"
  former_council VARCHAR(50),              -- e.g., "Marrickville", "Leichhardt", "Ashfield"

  -- PDF citation
  pdf_page INTEGER,
  pdf_source_file TEXT,
  pdf_page_image_url TEXT,

  -- Categorization
  domain_tags TEXT[],                      -- heritage, parking, setback, flood, tree, etc.

  -- Verification and metadata
  extraction_confidence NUMERIC(3,2) DEFAULT 1.0,  -- 0.00 to 1.00
  manual_verified BOOLEAN DEFAULT false,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  -- Unique constraint: same term from same source should not be duplicated
  UNIQUE (term_normalized, source_document)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_regulatory_definitions_term_normalized
  ON regulatory_definitions(term_normalized);

CREATE INDEX IF NOT EXISTS idx_regulatory_definitions_legislation_type
  ON regulatory_definitions(legislation_type);

CREATE INDEX IF NOT EXISTS idx_regulatory_definitions_former_council
  ON regulatory_definitions(former_council);

CREATE INDEX IF NOT EXISTS idx_regulatory_definitions_domain_tags
  ON regulatory_definitions USING GIN(domain_tags);

-- Full text search index on term and definition
CREATE INDEX IF NOT EXISTS idx_regulatory_definitions_fts
  ON regulatory_definitions
  USING GIN(to_tsvector('english', term || ' ' || definition_text));

-- Comment on table
COMMENT ON TABLE regulatory_definitions IS 'Structured definitions from DCP glossaries, SEPP Housing 2021, and Standard Instrument LEP';
COMMENT ON COLUMN regulatory_definitions.term_normalized IS 'Lowercase, stripped version of term for case-insensitive matching';
COMMENT ON COLUMN regulatory_definitions.legislation_type IS 'DCP = Development Control Plan, SEPP = State Environmental Planning Policy, SI_LEP = Standard Instrument LEP';
COMMENT ON COLUMN regulatory_definitions.domain_tags IS 'Categorization tags: heritage, parking, setback, flood, tree, stormwater, etc.';
