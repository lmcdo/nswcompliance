-- Migration: Create PostGIS-enabled precinct boundaries table
-- Purpose: Enable geometric point-in-polygon matching for precinct identification
-- Date: 2025-10-24

-- Step 1: Create PostGIS extensions (if not already installed)
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Step 2: Create precinct boundaries table with geometry column
CREATE TABLE IF NOT EXISTS dcp_precinct_boundaries (
  id SERIAL PRIMARY KEY,

  -- Precinct identification
  precinct_id TEXT NOT NULL,
  precinct_name TEXT NOT NULL,
  lga TEXT NOT NULL,
  former_council TEXT,  -- Marrickville, Ashfield, or Leichhardt (for Inner West)

  -- Geometric boundary (WGS84 coordinates - EPSG:4326)
  boundary GEOMETRY(POLYGON, 4326) NOT NULL,

  -- Centroid for quick reference
  centroid GEOMETRY(POINT, 4326),

  -- Metadata
  source_document TEXT,  -- PDF file boundary was extracted from
  extraction_method TEXT,  -- 'manual', 'digitized', 'api', 'approximated'
  confidence_score FLOAT DEFAULT 1.0,  -- 0.0-1.0 (how accurate is the boundary)
  boundary_description TEXT,  -- Human-readable description of boundary streets

  -- Area calculations
  area_sqm FLOAT,  -- Area in square metres
  perimeter_m FLOAT,  -- Perimeter in metres

  -- Timestamps
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  -- Constraints
  CONSTRAINT unique_precinct_lga UNIQUE (precinct_id, lga),
  CONSTRAINT valid_confidence CHECK (confidence_score >= 0 AND confidence_score <= 1)
);

-- Step 3: Create spatial index for fast point-in-polygon queries
-- GIST index is essential for geometric queries
CREATE INDEX idx_precinct_boundaries_geom
ON dcp_precinct_boundaries
USING GIST(boundary);

-- Step 4: Create standard indexes
CREATE INDEX idx_precinct_boundaries_lga
ON dcp_precinct_boundaries(lga);

CREATE INDEX idx_precinct_boundaries_precinct_id
ON dcp_precinct_boundaries(precinct_id);

CREATE INDEX idx_precinct_boundaries_former_council
ON dcp_precinct_boundaries(former_council)
WHERE former_council IS NOT NULL;

-- Step 5: Create trigger to auto-update centroid and area
CREATE OR REPLACE FUNCTION update_precinct_geometry_stats()
RETURNS TRIGGER AS $$
BEGIN
  -- Calculate centroid
  NEW.centroid = ST_Centroid(NEW.boundary);

  -- Calculate area in square metres (convert from degrees to metres)
  NEW.area_sqm = ST_Area(ST_Transform(NEW.boundary, 3857));

  -- Calculate perimeter in metres
  NEW.perimeter_m = ST_Perimeter(ST_Transform(NEW.boundary, 3857));

  -- Update timestamp
  NEW.updated_at = NOW();

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_precinct_geometry_stats
BEFORE INSERT OR UPDATE ON dcp_precinct_boundaries
FOR EACH ROW
EXECUTE FUNCTION update_precinct_geometry_stats();

-- Step 6: Create helper function for point-in-polygon matching
CREATE OR REPLACE FUNCTION find_precinct_for_coordinates(
  longitude FLOAT,
  latitude FLOAT,
  target_lga TEXT DEFAULT NULL
)
RETURNS TABLE (
  precinct_id TEXT,
  precinct_name TEXT,
  lga TEXT,
  confidence_score FLOAT,
  distance_from_centroid_m FLOAT
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    pb.precinct_id,
    pb.precinct_name,
    pb.lga,
    pb.confidence_score,
    ST_Distance(
      ST_Transform(pb.centroid, 3857),
      ST_Transform(ST_SetSRID(ST_MakePoint(longitude, latitude), 4326), 3857)
    ) as distance_from_centroid_m
  FROM dcp_precinct_boundaries pb
  WHERE ST_Contains(
    pb.boundary,
    ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
  )
  AND (target_lga IS NULL OR LOWER(pb.lga) = LOWER(target_lga))
  ORDER BY pb.confidence_score DESC, distance_from_centroid_m ASC
  LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Step 7: Create helper function to find nearest precinct (fallback if point not in any boundary)
CREATE OR REPLACE FUNCTION find_nearest_precinct(
  longitude FLOAT,
  latitude FLOAT,
  target_lga TEXT DEFAULT NULL,
  max_distance_m FLOAT DEFAULT 500
)
RETURNS TABLE (
  precinct_id TEXT,
  precinct_name TEXT,
  lga TEXT,
  confidence_score FLOAT,
  distance_from_boundary_m FLOAT
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    pb.precinct_id,
    pb.precinct_name,
    pb.lga,
    pb.confidence_score * 0.5 as confidence_score,  -- Reduce confidence for "nearest" matches
    ST_Distance(
      ST_Transform(pb.boundary, 3857),
      ST_Transform(ST_SetSRID(ST_MakePoint(longitude, latitude), 4326), 3857)
    ) as distance_from_boundary_m
  FROM dcp_precinct_boundaries pb
  WHERE (target_lga IS NULL OR LOWER(pb.lga) = LOWER(target_lga))
  AND ST_DWithin(
    ST_Transform(pb.boundary, 3857),
    ST_Transform(ST_SetSRID(ST_MakePoint(longitude, latitude), 4326), 3857),
    max_distance_m
  )
  ORDER BY distance_from_boundary_m ASC, pb.confidence_score DESC
  LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Step 8: Add comments for documentation
COMMENT ON TABLE dcp_precinct_boundaries IS 'Stores precinct boundary polygons for geometric address-to-precinct matching';
COMMENT ON COLUMN dcp_precinct_boundaries.boundary IS 'Polygon geometry in WGS84 (EPSG:4326) coordinates';
COMMENT ON COLUMN dcp_precinct_boundaries.centroid IS 'Auto-calculated centroid of the boundary polygon';
COMMENT ON COLUMN dcp_precinct_boundaries.extraction_method IS 'How the boundary was obtained: manual, digitized, api, or approximated';
COMMENT ON COLUMN dcp_precinct_boundaries.confidence_score IS 'Accuracy estimate (1.0 = highly accurate, 0.5 = approximated)';

COMMENT ON FUNCTION find_precinct_for_coordinates IS 'Find precinct containing a given coordinate point';
COMMENT ON FUNCTION find_nearest_precinct IS 'Find nearest precinct within max distance if point is not inside any boundary';

-- Step 9: Create view for easy precinct lookup with stats
CREATE OR REPLACE VIEW precinct_boundaries_with_stats AS
SELECT
  pb.id,
  pb.precinct_id,
  pb.precinct_name,
  pb.lga,
  pb.former_council,
  pb.extraction_method,
  pb.confidence_score,
  pb.area_sqm,
  ROUND((pb.area_sqm / 10000)::numeric, 2) as area_hectares,
  pb.perimeter_m,
  ST_AsGeoJSON(pb.boundary) as boundary_geojson,
  ST_AsText(pb.centroid) as centroid_wkt,
  pb.created_at,
  pb.updated_at,
  (SELECT COUNT(*) FROM dcp_precinct_provisions pp
   WHERE pp.precinct_id = pb.precinct_id AND pp.lga = pb.lga) as provision_count
FROM dcp_precinct_boundaries pb;

COMMENT ON VIEW precinct_boundaries_with_stats IS 'Precinct boundaries with calculated stats and provision counts';

-- Step 10: Grant permissions (adjust as needed)
-- GRANT SELECT ON dcp_precinct_boundaries TO your_app_user;
-- GRANT SELECT ON precinct_boundaries_with_stats TO your_app_user;
-- GRANT EXECUTE ON FUNCTION find_precinct_for_coordinates TO your_app_user;
-- GRANT EXECUTE ON FUNCTION find_nearest_precinct TO your_app_user;

-- Success message
DO $$
BEGIN
  RAISE NOTICE 'PostGIS precinct boundaries table created successfully!';
  RAISE NOTICE 'Next step: Run extract_precinct_boundaries.py to populate boundary data';
END $$;
