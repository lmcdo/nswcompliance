-- Migration: 002_add_heritage_columns
-- Description: Add heritage sub-categorization columns for DQ-11
-- Created: 2025-11-25
-- Feature: Heritage sub-categorization for Ashfield Chapter E1

-- Check if columns exist before adding (idempotent migration)
DO $$
BEGIN
    -- Heritage type classification
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'regulatory_provisions' AND column_name = 'v2_heritage_type') THEN
        ALTER TABLE regulatory_provisions ADD COLUMN v2_heritage_type TEXT;
        COMMENT ON COLUMN regulatory_provisions.v2_heritage_type IS 'Heritage sub-type: control, character, or descriptive';
    END IF;

    -- Heritage element tagging (array)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'regulatory_provisions' AND column_name = 'v2_heritage_element') THEN
        ALTER TABLE regulatory_provisions ADD COLUMN v2_heritage_element TEXT[];
        COMMENT ON COLUMN regulatory_provisions.v2_heritage_element IS 'Heritage elements: roof, verandah, window, fence, garden, etc.';
    END IF;

    -- Heritage Conservation Area name
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'regulatory_provisions' AND column_name = 'v2_heritage_hca') THEN
        ALTER TABLE regulatory_provisions ADD COLUMN v2_heritage_hca TEXT;
        COMMENT ON COLUMN regulatory_provisions.v2_heritage_hca IS 'HCA name: summer_hill, farleigh, harland, etc.';
    END IF;
END $$;

-- Create indexes for efficient heritage filtering
CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_v2_heritage_type
    ON regulatory_provisions(v2_heritage_type);

CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_v2_heritage_element
    ON regulatory_provisions USING GIN(v2_heritage_element);

CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_v2_heritage_hca
    ON regulatory_provisions(v2_heritage_hca);
