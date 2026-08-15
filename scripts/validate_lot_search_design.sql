-- Lot Search Index Design Validation
-- All queries are READ-ONLY. Safe to run against production.
-- Run with: psql $DATABASE_URL -f scripts/validate_lot_search_design.sql

-- Set statement timeout to 60s for safety
SET statement_timeout = '60s';

\echo '=== TEST 1: Bbox query speed on nsw_cadastre_lots (simulates JOIN approach) ==='
\echo 'Inner West area bbox — confirms GIST index works'
EXPLAIN ANALYZE
SELECT lotidstring, planlotarea, shape_area, urbanity
FROM nsw_cadastre_lots
WHERE ST_Intersects(geom, ST_MakeEnvelope(151.13, -33.91, 151.19, -33.86, 4326))
LIMIT 50;

\echo ''
\echo '=== TEST 2: Overlay spatial join via nsw_cadastre_lots (simulates rewritten build step) ==='
\echo 'Zone assignment for Inner West — confirms build script rewrite is viable'
EXPLAIN ANALYZE
SELECT DISTINCT ON (c.lotidstring)
    c.lotidstring, so.value
FROM nsw_cadastre_lots c
JOIN spatial_overlays so ON ST_Intersects(c.geom, so.geom)
WHERE so.layer_type = 'zone'
  AND so.lga_name = 'INNER WEST'
ORDER BY c.lotidstring, ST_Area(ST_Intersection(c.geom, so.geom)) DESC
LIMIT 10;

\echo ''
\echo '=== TEST 3: Storage — table sizes ==='
SELECT
    relname AS table_name,
    pg_size_pretty(pg_total_relation_size(c.oid)) AS total_size,
    pg_size_pretty(pg_relation_size(c.oid)) AS data_size,
    pg_size_pretty(pg_indexes_size(c.oid)) AS index_size,
    reltuples::bigint AS approx_rows
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND relname IN ('nsw_cadastre_lots', 'spatial_overlays', 'dcp_setback_controls',
                  'regulatory_provisions', 'development_applications',
                  'complying_development_certificates')
ORDER BY pg_total_relation_size(c.oid) DESC;

\echo ''
\echo '=== TEST 3b: Total database size ==='
SELECT pg_size_pretty(pg_database_size(current_database())) AS db_size;

\echo ''
\echo '=== TEST 3c: Average geometry size in nsw_cadastre_lots ==='
SELECT
    pg_size_pretty(avg(pg_column_size(geom))::bigint) AS avg_geom_size,
    pg_size_pretty((avg(pg_column_size(geom)) * count(*))::bigint) AS est_total_geom_size
FROM (SELECT geom FROM nsw_cadastre_lots TABLESAMPLE SYSTEM(0.1)) sample;

\echo ''
\echo '=== TEST 4: Lot counts per DCP LGA ==='
\echo 'How many lots in each council that has DCP setback data'
SELECT
    so.lga_name,
    COUNT(DISTINCT c.lotidstring) AS lot_count
FROM nsw_cadastre_lots c
JOIN spatial_overlays so ON ST_Intersects(c.geom, so.geom)
WHERE so.layer_type = 'zone'
  AND so.lga_name IN (
      SELECT DISTINCT UPPER(REPLACE(lga_slug, '_', ' '))
      FROM dcp_setback_controls
      WHERE is_current = TRUE
  )
GROUP BY so.lga_name
ORDER BY lot_count DESC;

\echo ''
\echo '=== TEST 5: NSW overlay coverage ==='
\echo 'How many LGAs have zone data in spatial_overlays'
SELECT
    COUNT(DISTINCT lga_name) AS lgas_with_zones,
    COUNT(*) AS total_zone_overlays
FROM spatial_overlays
WHERE layer_type = 'zone';

\echo ''
\echo '=== TEST 5b: All LGAs with zone data ==='
SELECT lga_name, COUNT(*) AS zone_count
FROM spatial_overlays
WHERE layer_type = 'zone' AND lga_name IS NOT NULL
GROUP BY lga_name
ORDER BY zone_count DESC;

\echo ''
\echo '=== TEST 6: GIST indexes present ==='
SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND (tablename IN ('nsw_cadastre_lots', 'spatial_overlays')
       AND indexdef ILIKE '%gist%')
ORDER BY tablename, indexname;

\echo ''
\echo '=== TEST 7: DCP LGA slugs in dcp_setback_controls ==='
SELECT lga_slug, COUNT(*) AS control_count
FROM dcp_setback_controls
WHERE is_current = TRUE
GROUP BY lga_slug
ORDER BY control_count DESC;

\echo ''
\echo '=== TEST 8: Scalar-only storage estimate ==='
\echo 'Average row size WITHOUT geometry (what lot_search_index would store)'
SELECT
    pg_size_pretty(avg(
        coalesce(pg_column_size(lotidstring), 0) +
        coalesce(pg_column_size(planlotarea), 0) +
        coalesce(pg_column_size(shape_area), 0) +
        coalesce(pg_column_size(urbanity), 0)
    )::bigint) AS avg_scalar_row_size,
    pg_size_pretty((avg(
        coalesce(pg_column_size(lotidstring), 0) +
        coalesce(pg_column_size(planlotarea), 0) +
        coalesce(pg_column_size(shape_area), 0) +
        coalesce(pg_column_size(urbanity), 0)
    ) * count(*))::bigint) AS est_total_scalar_all_nsw
FROM (SELECT * FROM nsw_cadastre_lots TABLESAMPLE SYSTEM(0.1)) sample;

\echo ''
\echo '=== DONE ==='
