-- Migration: 001_add_v2_columns
-- Description: Add v2_ columns to regulatory_provisions table for 4-layer filtering
-- Created: 2024-11-24
-- Feature: Provision-based architecture with 4-layer filtering model

-- Check if columns exist before adding (idempotent migration)
DO $$
BEGIN
    -- Core 4-layer columns
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'regulatory_provisions' AND column_name = 'v2_is_actionable') THEN
        ALTER TABLE regulatory_provisions ADD COLUMN v2_is_actionable BOOLEAN DEFAULT false;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'regulatory_provisions' AND column_name = 'v2_dcp_layer') THEN
        ALTER TABLE regulatory_provisions ADD COLUMN v2_dcp_layer TEXT;
        COMMENT ON COLUMN regulatory_provisions.v2_dcp_layer IS 'Layer classification: generic, use_specific, condition, precinct';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'regulatory_provisions' AND column_name = 'v2_dcp_part') THEN
        ALTER TABLE regulatory_provisions ADD COLUMN v2_dcp_part TEXT;
        COMMENT ON COLUMN regulatory_provisions.v2_dcp_part IS 'DCP part reference (e.g., Part 2, Section 1)';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'regulatory_provisions' AND column_name = 'v2_topic') THEN
        ALTER TABLE regulatory_provisions ADD COLUMN v2_topic TEXT;
        COMMENT ON COLUMN regulatory_provisions.v2_topic IS 'Topic classification: setbacks, parking, heritage, etc.';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'regulatory_provisions' AND column_name = 'v2_provision_type') THEN
        ALTER TABLE regulatory_provisions ADD COLUMN v2_provision_type TEXT;
        COMMENT ON COLUMN regulatory_provisions.v2_provision_type IS 'Type: control, objective, guideline, note';
    END IF;

    -- Precinct and marker columns
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'regulatory_provisions' AND column_name = 'v2_precinct_id') THEN
        ALTER TABLE regulatory_provisions ADD COLUMN v2_precinct_id TEXT;
        COMMENT ON COLUMN regulatory_provisions.v2_precinct_id IS 'Precinct identifier for Layer 4 filtering';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'regulatory_provisions' AND column_name = 'v2_marker') THEN
        ALTER TABLE regulatory_provisions ADD COLUMN v2_marker TEXT;
        COMMENT ON COLUMN regulatory_provisions.v2_marker IS 'DCP marker (e.g., C1, DS2, PC3)';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'regulatory_provisions' AND column_name = 'v2_display_behavior') THEN
        ALTER TABLE regulatory_provisions ADD COLUMN v2_display_behavior TEXT;
        COMMENT ON COLUMN regulatory_provisions.v2_display_behavior IS 'Display behavior: always, conditional, etc.';
    END IF;

    -- Filtering arrays for granular dev-type and zone matching
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'regulatory_provisions' AND column_name = 'v2_applicable_zones') THEN
        ALTER TABLE regulatory_provisions ADD COLUMN v2_applicable_zones TEXT[];
        COMMENT ON COLUMN regulatory_provisions.v2_applicable_zones IS 'Array of applicable zone codes (R2, R3, B1, etc.)';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'regulatory_provisions' AND column_name = 'v2_applicable_dev_types') THEN
        ALTER TABLE regulatory_provisions ADD COLUMN v2_applicable_dev_types TEXT[];
        COMMENT ON COLUMN regulatory_provisions.v2_applicable_dev_types IS 'Array of applicable development types (dwelling_house, dual_occupancy, etc.)';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'regulatory_provisions' AND column_name = 'v2_site_condition_required') THEN
        ALTER TABLE regulatory_provisions ADD COLUMN v2_site_condition_required TEXT;
        COMMENT ON COLUMN regulatory_provisions.v2_site_condition_required IS 'Required site condition: heritage, flood, bushfire, or NULL';
    END IF;

    -- CDC/DA assessment type support
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'regulatory_provisions' AND column_name = 'v2_has_numeric_value') THEN
        ALTER TABLE regulatory_provisions ADD COLUMN v2_has_numeric_value BOOLEAN DEFAULT false;
        COMMENT ON COLUMN regulatory_provisions.v2_has_numeric_value IS 'True if provision contains quantitative/checkable value (CDC-eligible)';
    END IF;

END $$;

-- Create indexes for efficient filtering
CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_v2_is_actionable
    ON regulatory_provisions(v2_is_actionable) WHERE v2_is_actionable = true;

CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_v2_dcp_layer
    ON regulatory_provisions(v2_dcp_layer);

CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_v2_topic
    ON regulatory_provisions(v2_topic);

CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_v2_precinct_id
    ON regulatory_provisions(v2_precinct_id);

CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_v2_applicable_zones
    ON regulatory_provisions USING GIN(v2_applicable_zones);

CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_v2_applicable_dev_types
    ON regulatory_provisions USING GIN(v2_applicable_dev_types);

-- Composite index for common query pattern
CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_v2_layer_topic
    ON regulatory_provisions(v2_dcp_layer, v2_topic) WHERE v2_is_actionable = true;
