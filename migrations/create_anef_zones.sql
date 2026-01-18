-- Create anef_zones table
-- Date: 2025-01-17
-- Purpose: Store Aircraft Noise Exposure Forecast zones for spatial queries

CREATE TABLE IF NOT EXISTS anef_zones (
    id SERIAL PRIMARY KEY,
    airport_code VARCHAR(10) NOT NULL,
    airport_name VARCHAR(100) NOT NULL,
    anef_version VARCHAR(50) NOT NULL,
    anef_level INTEGER NOT NULL,
    zone_type VARCHAR(20),
    geometry_json JSONB NOT NULL,
    bbox_min_lon NUMERIC(10, 6),
    bbox_max_lon NUMERIC(10, 6),
    bbox_min_lat NUMERIC(10, 6),
    bbox_max_lat NUMERIC(10, 6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_anef_zones_airport ON anef_zones(airport_code);
CREATE INDEX IF NOT EXISTS idx_anef_zones_level ON anef_zones(anef_level);
CREATE INDEX IF NOT EXISTS idx_anef_zones_bbox ON anef_zones(bbox_min_lon, bbox_max_lon, bbox_min_lat, bbox_max_lat);

COMMENT ON TABLE anef_zones IS 'ANEF zones digitised from airport master plan documents - AS2021:2015 standard';
COMMENT ON COLUMN anef_zones.anef_level IS 'ANEF contour level (20, 25, 30, 35, 40)';
COMMENT ON COLUMN anef_zones.geometry_json IS 'Full polygon geometry in GeoJSON format';
COMMENT ON COLUMN anef_zones.bbox_min_lon IS 'Bounding box for fast spatial filtering';
