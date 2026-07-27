-- Sydney Water Growth Servicing Plan (GSP) serviceability layer.
--
-- New, standalone table — NOT spatial_overlays. spatial_overlays is modelled around
-- LEP instruments / LGAs with a bigint source_oid and no attributes column; GSP
-- polygons carry none of that and need ~8 signal fields, so they get their own table.
-- Additive only: creating this table touches no existing data. Reverse with DROP TABLE.
--
-- Source: 3 public GeoJSON files on the Sydney Water CDN (GSP_WW / GSP_DW), 205 WW +
-- 192 DW WGS84 polygons. Ingested by scripts/ingest_sydney_water_gsp.py.
--
-- Field decisions (see docs/servicing/gsp-smoketest-findings.md):
--   * dsp_price_per_et  = leading $ figure parsed out of the HTML blob (nullable; $0 is
--       valid; ~14 rows carry no figure). It is a BASE snapshot — the live charge is CPI-
--       adjusted, so dsp_price_raw keeps the source string and callers must show the
--       CPI caveat + link, never present this number as the definitive current charge.
--   * Existing_Servicing_Information is deliberately NOT stored — it is the identical
--       dead pointer "Refer to GSP2025-2030 PDF document." on every row (zero signal).
--   * status_code is derived, not from source: IN_DELIVERY | PLANNED | NO_CURRENT_PROJECT,
--       with constrained=true overlaying CONSTRAINED at read time.

CREATE TABLE IF NOT EXISTS sydney_water_gsp_servicing (
    id                bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product           text        NOT NULL,          -- 'WW' (wastewater) | 'DW' (drinking water)
    swc_id            text        NOT NULL,          -- raw SWC_Unique_Identifier, e.g. 'WW87'
    polygon_name      text,                          -- Growth_Polygon_Name
    growth_area       text,                          -- Growth_Area
    status_code       text        NOT NULL,          -- IN_DELIVERY | PLANNED | NO_CURRENT_PROJECT
    stage             text,                          -- raw SWC_Planning_Project_Stage
    timeframe         text,                          -- raw Indicative_Timeframe_by_Financial_Year(FY)
    dsp_price_per_et  double precision,              -- parsed base $ (nullable; $0 valid)
    dsp_price_raw     text,                          -- HTML-stripped source string incl. CPI caveat
    dsp_area          text,                          -- Development_Servicing_Plan_(DSP)_Area
    constrained       boolean     NOT NULL DEFAULT false,  -- capacity/timescale constraint note present
    special_comments  text,                          -- the constraint note itself (WW only)
    commentary        text,                          -- GSP_Commentary
    source_snapshot   text        NOT NULL DEFAULT 'GSP2025-2030',
    geom              geometry(MultiPolygon, 4326) NOT NULL,
    synced_at         timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT sydney_water_gsp_product_chk CHECK (product IN ('WW','DW')),
    CONSTRAINT sydney_water_gsp_status_chk
        CHECK (status_code IN ('IN_DELIVERY','PLANNED','NO_CURRENT_PROJECT','UNKNOWN_STAGE')),
    CONSTRAINT sydney_water_gsp_product_swc_key UNIQUE (product, swc_id)  -- annual-refresh upsert key
);

CREATE INDEX IF NOT EXISTS sydney_water_gsp_geom_gix
    ON sydney_water_gsp_servicing USING gist (geom);

CREATE INDEX IF NOT EXISTS sydney_water_gsp_status_idx
    ON sydney_water_gsp_servicing (status_code);

COMMENT ON TABLE sydney_water_gsp_servicing IS
    'Sydney Water Growth Servicing Plan polygons (WW+DW). Growth-area coverage only; a '
    'point outside every polygon is UNKNOWN (Section 73 territory), not a negative status. '
    'dsp_price_per_et is a CPI-excluded base snapshot — never present as the live charge. '
    'Source is © Sydney Water, "guide only" — licence/attribution required before external redistribution.';
