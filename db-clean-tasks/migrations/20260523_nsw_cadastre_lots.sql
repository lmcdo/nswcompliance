-- NSW Cadastre Lots table
-- Source: NSW Spatial Services FeatureServer Layer 8
-- URL: https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Land_Parcel_Property_Theme/FeatureServer/8
-- License: CC-BY 4.0 (commercial use OK with attribution)
-- Records: ~3.35M lots statewide

CREATE TABLE IF NOT EXISTS nsw_cadastre_lots (
    id              bigserial PRIMARY KEY,
    lotidstring     text NOT NULL UNIQUE,       -- e.g. "1//DP550708"
    lotnumber       text,
    sectionnumber   text,
    planlabel       text,
    plannumber      text,
    planlotarea     double precision,            -- plan-registered area (m²), sometimes null
    shape_area      double precision NOT NULL,   -- calculated geometry area (m²)
    urbanity        text,                        -- "U" (urban) or "R" (rural)
    stratumlevel    text,
    hasstratum      text,
    itstitlestatus  text,
    createdate      timestamptz,
    modifieddate    timestamptz,
    cadid           bigint,
    objectid        bigint,                      -- ArcGIS source OID for incremental sync
    geom            geometry(MultiPolygon, 4326), -- reprojected from EPSG:3857
    synced_at       timestamptz NOT NULL DEFAULT now()
);

-- Spatial index for PostGIS intersection queries (Prospector filtering)
CREATE INDEX IF NOT EXISTS idx_cadastre_lots_geom ON nsw_cadastre_lots USING GIST (geom);

-- Urbanity filter (most queries target urban lots only)
CREATE INDEX IF NOT EXISTS idx_cadastre_lots_urbanity ON nsw_cadastre_lots (urbanity);

-- Area range queries for lot size filtering
CREATE INDEX IF NOT EXISTS idx_cadastre_lots_area ON nsw_cadastre_lots (shape_area);

-- Incremental sync: find lots modified since last run
CREATE INDEX IF NOT EXISTS idx_cadastre_lots_modified ON nsw_cadastre_lots (modifieddate);

-- Plan lookup (join with VG data via lot/plan identifiers)
CREATE INDEX IF NOT EXISTS idx_cadastre_lots_planlabel ON nsw_cadastre_lots (planlabel);

COMMENT ON TABLE nsw_cadastre_lots IS 'NSW cadastre lot polygons from Spatial Services FeatureServer. CC-BY 4.0. ~3.35M lots.';
