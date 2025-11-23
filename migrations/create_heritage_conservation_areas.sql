-- Create heritage_conservation_areas table
-- Date: 2025-10-12
-- Purpose: Restore table lost in database recovery

CREATE TABLE IF NOT EXISTS heritage_conservation_areas (
    id SERIAL PRIMARY KEY,
    objectid INTEGER UNIQUE NOT NULL,
    h_id VARCHAR(50),
    h_name TEXT,
    significance TEXT,
    legislative_clause TEXT,
    lay_class VARCHAR(100),
    epi_name TEXT,
    lga_name VARCHAR(100),
    published_date TIMESTAMP,
    commenced_date TIMESTAMP,
    currency_date TIMESTAMP,
    amendment TEXT,
    pco_ref_key VARCHAR(100),
    epi_type VARCHAR(50),
    geometry_json JSONB,
    bbox_min_x NUMERIC,
    bbox_min_y NUMERIC,
    bbox_max_x NUMERIC,
    bbox_max_y NUMERIC,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_hca_lga_name ON heritage_conservation_areas(lga_name);
CREATE INDEX IF NOT EXISTS idx_hca_h_id ON heritage_conservation_areas(h_id);
CREATE INDEX IF NOT EXISTS idx_hca_bbox ON heritage_conservation_areas(bbox_min_x, bbox_min_y, bbox_max_x, bbox_max_y);
CREATE INDEX IF NOT EXISTS idx_hca_h_name ON heritage_conservation_areas USING gin(to_tsvector('english', h_name));

COMMENT ON TABLE heritage_conservation_areas IS 'NSW Heritage Conservation Areas from Planning Portal - imported from GeoJSON';
COMMENT ON COLUMN heritage_conservation_areas.geometry_json IS 'Full polygon geometry in GeoJSON format';
COMMENT ON COLUMN heritage_conservation_areas.bbox_min_x IS 'Bounding box for fast spatial filtering';
