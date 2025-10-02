-- Migration: Add SEPP relationship tables for proper Planning Portal integration
-- Purpose: Link SEPP provisions to maps, amendments, climate zones, and geographic areas
-- Date: 2025-09-30

-- BACKUP FIRST: pg_dump -U postgres nsw_planning > backup_before_sepp_tables.sql

BEGIN;

-- 1. SEPP Metadata - Track all SEPPs and their versions
CREATE TABLE IF NOT EXISTS sepp_metadata (
    id SERIAL PRIMARY KEY,
    sepp_name TEXT NOT NULL UNIQUE,
    document_id TEXT,
    commenced_date DATE,
    current_version_date DATE,
    epi_number TEXT,  -- e.g. '2021-732', '2022-825'
    epi_type TEXT DEFAULT 'SEPP',
    supersedes TEXT,  -- Previous SEPP name if this replaces one
    repealed_by TEXT,  -- SEPP that repeals this one (if applicable)
    amendments JSONB DEFAULT '[]'::jsonb,  -- [{name, date, epi_number}]
    created_at TIMESTAMP DEFAULT NOW()
);

-- 2. SEPP Amendments - Track amendments and what they change
CREATE TABLE IF NOT EXISTS sepp_amendments (
    id SERIAL PRIMARY KEY,
    amendment_name TEXT NOT NULL,
    base_sepp_id INTEGER REFERENCES sepp_metadata(id),
    amendment_date DATE,
    commenced_date DATE,
    published_date DATE,
    epi_number TEXT,  -- e.g. '2022-825' for Thermal Waste Amendment
    amendment_type TEXT,  -- 'adds', 'modifies', 'repeals', 'prohibits'
    affected_provision_ids INTEGER[],
    amendment_document_id TEXT,
    summary TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 3. SEPP Maps - All maps referenced by SEPPs
CREATE TABLE IF NOT EXISTS sepp_maps (
    id SERIAL PRIMARY KEY,
    map_name TEXT NOT NULL,
    map_type TEXT NOT NULL,  -- 'TEW', 'BAL', 'CLM', 'HER', 'FSR', 'HOB', etc.
    sepp_metadata_id INTEGER REFERENCES sepp_metadata(id),
    sepp_document_id TEXT,
    provision_ids INTEGER[],  -- Provisions that reference this map
    map_url TEXT,  -- URL to map if available
    geometry_data JSONB,  -- GeoJSON boundaries if available
    applies_to_lgas TEXT[],  -- LGAs covered by this map
    geographic_scope TEXT,  -- 'Greater Sydney', 'NSW-wide', 'Regional', etc.
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(map_name, map_type)
);

-- 4. Climate Zones - Structured climate zone data
CREATE TABLE IF NOT EXISTS climate_zones (
    id SERIAL PRIMARY KEY,
    zone_number INTEGER,  -- e.g. 2049, 5, 17
    zone_name TEXT,  -- e.g. 'INNER WEST', 'COASTAL'
    sepp_map_id INTEGER REFERENCES sepp_maps(id),
    map_type TEXT,  -- 'BAL' (alterations) or 'CLM' (buildings)
    lgas TEXT[],
    postcodes TEXT[],
    suburbs TEXT[],
    provisions_by_zone JSONB,  -- {thermal_performance: '...', energy_standard: '...'}
    created_at TIMESTAMP DEFAULT NOW()
);

-- 5. Water Use Zones - Structured water reduction requirements
CREATE TABLE IF NOT EXISTS water_use_zones (
    id SERIAL PRIMARY KEY,
    area_designation TEXT,  -- 'Area A', 'Area B'
    reduction_percentage INTEGER,  -- 0, 10, 20, 30, 40
    lgas TEXT[],
    postcodes TEXT[],
    suburbs TEXT[],
    provision_id INTEGER REFERENCES regulatory_provisions(id),
    sepp_map_id INTEGER REFERENCES sepp_maps(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 6. Planning Portal Map Detection - Store what Planning Portal detects
CREATE TABLE IF NOT EXISTS planning_portal_map_detections (
    id SERIAL PRIMARY KEY,
    property_address TEXT,
    lat NUMERIC,
    lng NUMERIC,
    map_type TEXT,  -- What PP calls it: 'TEW', 'BAL', 'CLM', etc.
    map_name TEXT,  -- Full name from PP
    epi_name TEXT,  -- SEPP name from PP
    epi_type TEXT,  -- Usually 'SEPP'
    commenced_date DATE,
    currency_date DATE,
    published_date DATE,
    amendment TEXT,  -- Amendment name if applicable
    class_value TEXT,  -- e.g. '5', '56', '40%'
    type_value TEXT,  -- e.g. 'Climate Zones', 'Greater Sydney'
    label_value TEXT,  -- e.g. 'INNER WEST', '2049'
    raw_detection_data JSONB,  -- Full JSON from Planning Portal
    sepp_map_id INTEGER REFERENCES sepp_maps(id),  -- Link to our maps
    detected_at TIMESTAMP DEFAULT NOW()
);

-- 7. Add new columns to regulatory_provisions
ALTER TABLE regulatory_provisions
    ADD COLUMN IF NOT EXISTS sepp_metadata_id INTEGER REFERENCES sepp_metadata(id),
    ADD COLUMN IF NOT EXISTS map_references TEXT[],  -- ['TEW', 'BAL', 'CLM']
    ADD COLUMN IF NOT EXISTS geographic_scope TEXT,  -- 'Greater Sydney', 'NSW-wide', etc.
    ADD COLUMN IF NOT EXISTS applies_to_zones TEXT[],  -- Climate zones
    ADD COLUMN IF NOT EXISTS applies_to_lgas TEXT[];  -- Specific LGAs

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_sepp_metadata_document_id ON sepp_metadata(document_id);
CREATE INDEX IF NOT EXISTS idx_sepp_amendments_base_sepp ON sepp_amendments(base_sepp_id);
CREATE INDEX IF NOT EXISTS idx_sepp_amendments_epi_number ON sepp_amendments(epi_number);
CREATE INDEX IF NOT EXISTS idx_sepp_maps_type ON sepp_maps(map_type);
CREATE INDEX IF NOT EXISTS idx_sepp_maps_sepp_id ON sepp_maps(sepp_metadata_id);
CREATE INDEX IF NOT EXISTS idx_climate_zones_number ON climate_zones(zone_number);
CREATE INDEX IF NOT EXISTS idx_water_use_zones_lgas ON water_use_zones USING GIN(lgas);
CREATE INDEX IF NOT EXISTS idx_planning_portal_map_type ON planning_portal_map_detections(map_type);
CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_sepp_id ON regulatory_provisions(sepp_metadata_id);
CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_map_refs ON regulatory_provisions USING GIN(map_references);

COMMIT;

-- Verification queries
-- SELECT * FROM sepp_metadata;
-- SELECT * FROM sepp_maps;
-- SELECT * FROM climate_zones;