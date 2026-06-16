-- Migration 048: Create lot_search_index table
-- Pre-computed spatial join of cadastre lots with overlays + constraint arithmetic results.
-- Enables sub-second bulk property search for professional "find me lots" queries.

CREATE TABLE IF NOT EXISTS lot_search_index (
    lotidstring            TEXT PRIMARY KEY,
    lga_name               TEXT,
    zone_code              TEXT,
    lep_height_m           DOUBLE PRECISION,
    lep_fsr                DOUBLE PRECISION,
    lot_area_m2            DOUBLE PRECISION,
    urbanity               TEXT,
    heritage               BOOLEAN DEFAULT FALSE,
    heritage_type          TEXT,
    flood_prone            BOOLEAN DEFAULT FALSE,
    bushfire_prone         BOOLEAN DEFAULT FALSE,
    bushfire_category      TEXT,
    acid_sulfate           BOOLEAN DEFAULT FALSE,
    -- Constraint arithmetic results (NULL if not computable)
    ca_dev_type            TEXT,
    ca_realistic_gfa_m2    DOUBLE PRECISION,
    ca_realistic_dwellings INTEGER,
    ca_binding_constraint  TEXT,
    ca_effective_height_m  DOUBLE PRECISION,
    ca_effective_fsr       DOUBLE PRECISION,
    ca_confidence          TEXT,
    ca_setback_front_m     DOUBLE PRECISION,
    ca_setback_rear_m      DOUBLE PRECISION,
    ca_setback_side_m      DOUBLE PRECISION,
    ca_buildable_footprint_m2 DOUBLE PRECISION,
    ca_lep_envelope_gfa_m2 DOUBLE PRECISION,
    ca_gaps                TEXT[],
    -- Former council area (for merged LGAs like Inner West → ashfield/leichhardt/marrickville)
    former_council         TEXT,
    -- Metadata
    computed_at            TIMESTAMPTZ DEFAULT NOW(),
    geom                   geometry(MultiPolygon, 4326)
);

-- Scalar indexes for common search filters
CREATE INDEX IF NOT EXISTS idx_lsi_lga ON lot_search_index (lga_name);
CREATE INDEX IF NOT EXISTS idx_lsi_zone ON lot_search_index (zone_code);
CREATE INDEX IF NOT EXISTS idx_lsi_area ON lot_search_index (lot_area_m2);
CREATE INDEX IF NOT EXISTS idx_lsi_gfa ON lot_search_index (ca_realistic_gfa_m2);
CREATE INDEX IF NOT EXISTS idx_lsi_dwellings ON lot_search_index (ca_realistic_dwellings);
CREATE INDEX IF NOT EXISTS idx_lsi_confidence ON lot_search_index (ca_confidence);
CREATE INDEX IF NOT EXISTS idx_lsi_binding ON lot_search_index (ca_binding_constraint);

-- Spatial index for bounding-box and proximity queries
CREATE INDEX IF NOT EXISTS idx_lsi_geom ON lot_search_index USING GIST (geom);

CREATE INDEX IF NOT EXISTS idx_lsi_former_council ON lot_search_index (former_council);

-- Composite indexes for the most common filter combinations
CREATE INDEX IF NOT EXISTS idx_lsi_lga_zone_area
    ON lot_search_index (lga_name, zone_code, lot_area_m2);
CREATE INDEX IF NOT EXISTS idx_lsi_zone_area_gfa
    ON lot_search_index (zone_code, lot_area_m2, ca_realistic_gfa_m2);
