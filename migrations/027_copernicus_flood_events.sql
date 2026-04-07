-- 027_copernicus_flood_events.sql
-- Stores Copernicus EMS activation flood extents for Australia.
-- Used by flood_truth.py to fill the Sentinel-1B gap (Dec 2021 – Mar 2025).
-- Ingestion: python scripts/ingest_copernicus_ems.py <file.geojson> ...

CREATE TABLE IF NOT EXISTS copernicus_flood_events (
    id               SERIAL PRIMARY KEY,
    activation_id    TEXT        NOT NULL,          -- e.g. 'EMSR531'
    event_name       TEXT        NOT NULL,
    event_date_start DATE        NOT NULL,
    event_date_end   DATE        NOT NULL,
    geometry         GEOMETRY(MULTIPOLYGON, 4326) NOT NULL,
    flood_type       TEXT        NOT NULL DEFAULT 'observed',  -- 'observed' | 'estimated'
    country          TEXT        NOT NULL DEFAULT 'AU',
    source_url       TEXT,
    ingested_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS copernicus_flood_events_geom_idx
    ON copernicus_flood_events USING GIST (geometry);

CREATE INDEX IF NOT EXISTS copernicus_flood_events_activation_idx
    ON copernicus_flood_events (activation_id);

COMMENT ON TABLE copernicus_flood_events IS
    'Copernicus EMS Rapid Mapping flood extent polygons for Australian activations. '
    'Primary use: fill Sentinel-1B gap (Dec 2021 – Mar 2025) in flood_truth pipeline.';
