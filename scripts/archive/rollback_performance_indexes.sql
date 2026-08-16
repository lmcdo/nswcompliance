-- ============================================================
-- NSW Planning Compliance Engine
-- Rollback Script for Performance Indexes
-- ============================================================
--
-- SAFETY: This script uses CONCURRENTLY to avoid locking tables
-- Only use this if indexes are causing issues
--
-- ============================================================

\echo '============================================================'
\echo 'ROLLBACK: Removing Performance Indexes'
\echo '============================================================'
\echo ''
\echo 'This will remove the 6 indexes added by add_performance_indexes_safe.sql'
\echo ''

-- Drop GIN indexes
\echo '[1/6] Dropping idx_dcp_gen_req_zones_gin...'
DROP INDEX CONCURRENTLY IF EXISTS idx_dcp_gen_req_zones_gin;
\echo '      ✓ Dropped'

\echo '[2/6] Dropping idx_dcp_gen_req_devtypes_gin...'
DROP INDEX CONCURRENTLY IF EXISTS idx_dcp_gen_req_devtypes_gin;
\echo '      ✓ Dropped'

\echo '[3/6] Dropping idx_dcp_gen_prov_zones_gin...'
DROP INDEX CONCURRENTLY IF EXISTS idx_dcp_gen_prov_zones_gin;
\echo '      ✓ Dropped'

\echo '[4/6] Dropping idx_dcp_gen_prov_devtypes_gin...'
DROP INDEX CONCURRENTLY IF EXISTS idx_dcp_gen_prov_devtypes_gin;
\echo '      ✓ Dropped'

-- Drop B-tree indexes
\echo '[5/6] Dropping idx_dcp_gen_req_former_council...'
DROP INDEX CONCURRENTLY IF EXISTS idx_dcp_gen_req_former_council;
\echo '      ✓ Dropped'

\echo '[6/6] Dropping idx_reg_prov_document_id...'
DROP INDEX CONCURRENTLY IF EXISTS idx_reg_prov_document_id;
\echo '      ✓ Dropped'

\echo ''
\echo 'Rollback complete. All performance indexes removed.'
\echo ''
