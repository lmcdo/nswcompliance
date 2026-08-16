-- ============================================================
-- NSW Planning Compliance Engine
-- Performance Optimization Indexes - SAFE EXECUTION
-- Generated: 2025-11-10
--
-- SAFETY FEATURES:
-- 1. IF NOT EXISTS prevents duplicate index errors
-- 2. CONCURRENTLY allows queries during index creation
-- 3. Rollback plan included at bottom
-- 4. Verification queries included
-- ============================================================

-- BEFORE RUNNING: Create backup
-- pg_dump -h localhost -U postgres -d nsw_planning -F c -f nsw_planning_before_indexes_$(date +%Y%m%d_%H%M%S).backup

\echo '============================================================'
\echo 'Performance Index Creation - Safe Mode'
\echo '============================================================'
\echo ''
\echo 'This script will add 6 indexes to improve query performance.'
\echo 'All indexes use IF NOT EXISTS and CONCURRENTLY for safety.'
\echo ''

-- Show current database size before indexing
\echo 'Current database size:'
SELECT
  pg_size_pretty(pg_database_size('nsw_planning')) as total_size;

\echo ''
\echo '============================================================'
\echo 'Step 1: GIN Indexes for Array Queries (Priority 1)'
\echo '============================================================'
\echo ''

-- DCP General Requirements: applicable_zones
\echo '[1/6] Creating GIN index on dcp_general_requirements(applicable_zones)...'
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dcp_gen_req_zones_gin
  ON dcp_general_requirements USING GIN (applicable_zones);

\echo '      ✓ Index created'
\echo '      Impact: Speeds up zone filtering in Ashfield queries'
\echo '      Used in: frontend-nextjs/app/api/compliance/dcp-complete/route.ts:857'
\echo ''

-- DCP General Requirements: development_types
\echo '[2/6] Creating GIN index on dcp_general_requirements(development_types)...'
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dcp_gen_req_devtypes_gin
  ON dcp_general_requirements USING GIN (development_types);

\echo '      ✓ Index created'
\echo '      Impact: Speeds up development type filtering'
\echo '      Used in: frontend-nextjs/app/api/compliance/dcp-complete/route.ts:858'
\echo ''

-- DCP General Provisions: applicable_zones
\echo '[3/6] Creating GIN index on dcp_general_provisions(applicable_zones)...'
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dcp_gen_prov_zones_gin
  ON dcp_general_provisions USING GIN (applicable_zones);

\echo '      ✓ Index created'
\echo '      Impact: Speeds up provision filtering by zone'
\echo '      Used in: frontend-nextjs/app/api/compliance/dcp-complete/route.ts:206'
\echo ''

-- DCP General Provisions: development_types
\echo '[4/6] Creating GIN index on dcp_general_provisions(development_types)...'
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dcp_gen_prov_devtypes_gin
  ON dcp_general_provisions USING GIN (development_types);

\echo '      ✓ Index created'
\echo '      Impact: Speeds up provision filtering by development type'
\echo '      Used in: frontend-nextjs/app/api/compliance/dcp-complete/route.ts:207'
\echo ''

\echo '============================================================'
\echo 'Step 2: Core Query Indexes (Priority 1)'
\echo '============================================================'
\echo ''

-- DCP General Requirements: former_council
\echo '[5/6] Creating B-tree index on dcp_general_requirements(former_council)...'
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_dcp_gen_req_former_council
  ON dcp_general_requirements(former_council);

\echo '      ✓ Index created'
\echo '      Impact: Critical for Inner West council filtering'
\echo '      Used in: frontend-nextjs/app/api/compliance/dcp-complete/route.ts:859,891,922'
\echo ''

-- Regulatory Provisions: document_id
\echo '[6/6] Creating B-tree index on regulatory_provisions(document_id)...'
\echo '      WARNING: This table has 48,087 rows - may take 30-60 seconds'
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_reg_prov_document_id
  ON regulatory_provisions(document_id);

\echo '      ✓ Index created'
\echo '      Impact: Critical for fallback query performance'
\echo '      Used in: frontend-nextjs/app/api/compliance/dcp-complete/route.ts:358,508'
\echo ''

\echo '============================================================'
\echo 'Step 3: Verification'
\echo '============================================================'
\echo ''

-- Show newly created indexes
\echo 'Newly created indexes:'
SELECT
  schemaname,
  tablename,
  indexname,
  pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
  idx_scan as times_used
FROM pg_stat_user_indexes
WHERE indexname IN (
  'idx_dcp_gen_req_zones_gin',
  'idx_dcp_gen_req_devtypes_gin',
  'idx_dcp_gen_prov_zones_gin',
  'idx_dcp_gen_prov_devtypes_gin',
  'idx_dcp_gen_req_former_council',
  'idx_reg_prov_document_id'
)
ORDER BY tablename, indexname;

\echo ''

-- Show total database size after indexing
\echo 'Database size after indexing:'
SELECT
  pg_size_pretty(pg_database_size('nsw_planning')) as total_size;

\echo ''

-- Show index sizes by table
\echo 'Index sizes by table:'
SELECT
  tablename,
  pg_size_pretty(pg_indexes_size(tablename::regclass)) AS total_index_size,
  COUNT(*) as index_count
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename IN (
    'dcp_general_requirements',
    'dcp_general_provisions',
    'regulatory_provisions'
  )
GROUP BY tablename
ORDER BY pg_indexes_size(tablename::regclass) DESC;

\echo ''

-- Update table statistics (critical for query planner)
\echo 'Updating table statistics for query planner...'
ANALYZE dcp_general_requirements;
ANALYZE dcp_general_provisions;
ANALYZE regulatory_provisions;

\echo '      ✓ Statistics updated'
\echo ''

\echo '============================================================'
\echo 'SUCCESS: All indexes created'
\echo '============================================================'
\echo ''
\echo 'Next steps:'
\echo '1. Test API performance with: python scripts/test_api_performance.py'
\echo '2. Monitor slow query log: Check for queries >1000ms'
\echo '3. Verify index usage with EXPLAIN ANALYZE on key queries'
\echo ''
\echo 'If you need to rollback, run: \\i scripts/rollback_performance_indexes.sql'
\echo ''

-- ============================================================
-- ROLLBACK SCRIPT (save as scripts/rollback_performance_indexes.sql)
-- ============================================================
-- DROP INDEX CONCURRENTLY IF EXISTS idx_dcp_gen_req_zones_gin;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_dcp_gen_req_devtypes_gin;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_dcp_gen_prov_zones_gin;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_dcp_gen_prov_devtypes_gin;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_dcp_gen_req_former_council;
-- DROP INDEX CONCURRENTLY IF EXISTS idx_reg_prov_document_id;
-- ============================================================
