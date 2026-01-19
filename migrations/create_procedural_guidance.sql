-- Migration: Create procedural_guidance and application_checklists tables
-- Purpose: Store procedural workflow Q&A for AI assistant
-- Date: 2026-01-19

-- Table: procedural_guidance
-- Stores question-answer pairs for workflow/process questions
CREATE TABLE IF NOT EXISTS procedural_guidance (
  id SERIAL PRIMARY KEY,

  -- Question mapping
  question_pattern TEXT NOT NULL,           -- "Should I use CDC or DA?"
  question_normalized TEXT NOT NULL,        -- lowercase for matching
  question_category VARCHAR(50) NOT NULL,   -- pathway, checklist, timeline, professional

  -- Answer content
  answer_summary TEXT NOT NULL,             -- Brief answer (1-2 sentences)
  answer_detailed TEXT NOT NULL,            -- Full answer with steps
  answer_conditions TEXT[],                 -- Conditions that affect the answer

  -- Source citation
  source_document TEXT NOT NULL,            -- "NSW Planning Portal - Apply for CDC"
  source_url TEXT,                          -- Direct URL to source
  source_section TEXT,                      -- Section/heading within document
  last_verified DATE,                       -- When source was last checked

  -- Related questions
  follow_up_questions TEXT[],               -- Suggested next questions
  related_question_ids INTEGER[],           -- Links to related Q&A

  -- Applicability
  applies_to_cdc BOOLEAN DEFAULT true,
  applies_to_da BOOLEAN DEFAULT true,
  applies_to_dev_types TEXT[],              -- dual_occ, manor_house, etc.

  -- Metadata
  extraction_confidence NUMERIC(3,2) DEFAULT 1.0,
  manual_verified BOOLEAN DEFAULT false,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  UNIQUE (question_normalized, source_document)
);

-- Table: application_checklists
-- Stores document requirements for CDC/DA applications
CREATE TABLE IF NOT EXISTS application_checklists (
  id SERIAL PRIMARY KEY,

  -- Checklist identification
  checklist_name TEXT NOT NULL,             -- "CDC Application Checklist"
  pathway VARCHAR(10) NOT NULL,             -- CDC, DA
  development_type TEXT,                    -- dual_occ, manor_house, dwelling_house

  -- Checklist items
  item_order INTEGER NOT NULL,
  item_name TEXT NOT NULL,                  -- "Site Plan"
  item_description TEXT,                    -- Details about the requirement
  item_required BOOLEAN DEFAULT true,       -- Required vs optional
  item_conditions TEXT,                     -- When this item is required

  -- Source
  source_document TEXT NOT NULL,
  source_url TEXT,

  -- Metadata
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

  UNIQUE (checklist_name, item_order)
);

-- Indexes for procedural_guidance
CREATE INDEX IF NOT EXISTS idx_procedural_guidance_category
  ON procedural_guidance(question_category);

CREATE INDEX IF NOT EXISTS idx_procedural_guidance_pathway
  ON procedural_guidance(applies_to_cdc, applies_to_da);

CREATE INDEX IF NOT EXISTS idx_procedural_guidance_fts
  ON procedural_guidance
  USING GIN(to_tsvector('english', question_pattern || ' ' || answer_summary));

-- Indexes for application_checklists
CREATE INDEX IF NOT EXISTS idx_application_checklists_pathway
  ON application_checklists(pathway);

CREATE INDEX IF NOT EXISTS idx_application_checklists_dev_type
  ON application_checklists(development_type);

-- Comments
COMMENT ON TABLE procedural_guidance IS 'Q&A pairs for procedural/workflow questions about CDC and DA processes';
COMMENT ON TABLE application_checklists IS 'Document checklists for CDC and DA applications';
COMMENT ON COLUMN procedural_guidance.question_category IS 'Categories: pathway, checklist, timeline, professional';
COMMENT ON COLUMN procedural_guidance.answer_conditions IS 'Conditions that may change the answer (e.g., heritage site, flood zone)';
