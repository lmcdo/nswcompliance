-- ============================================
-- DB CLEANUP INVESTIGATION QUERIES
-- Run these in Supabase SQL Editor
-- ============================================

-- ============================================
-- 1. CHECK CURRENT DATABASE SIZE
-- ============================================
SELECT
  pg_size_pretty(pg_database_size(current_database())) as total_db_size;

-- Top 20 tables by size
SELECT
  tablename,
  pg_size_pretty(pg_total_relation_size('public.' || tablename)) as total_size,
  pg_size_pretty(pg_relation_size('public.' || tablename)) as table_size,
  pg_size_pretty(pg_indexes_size('public.' || tablename)) as index_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size('public.' || tablename) DESC
LIMIT 20;

-- ============================================
-- 2. PRECINCT_BOUNDARIES vs DCP_PRECINCT_BOUNDARIES
-- Are they duplicates?
-- ============================================

-- Compare row counts and sample data
SELECT 'precinct_boundaries' as table_name, COUNT(*) as rows FROM precinct_boundaries
UNION ALL
SELECT 'dcp_precinct_boundaries', COUNT(*) FROM dcp_precinct_boundaries;

-- Check if precinct_boundaries IDs exist in dcp_precinct_boundaries
SELECT
  pb.precinct_id as old_precinct_id,
  pb.precinct_name as old_name,
  pb.lga as old_lga,
  dpb.precinct_id as new_precinct_id,
  dpb.precinct_name as new_name
FROM precinct_boundaries pb
LEFT JOIN dcp_precinct_boundaries dpb
  ON pb.precinct_id = dpb.precinct_id OR pb.precinct_name = dpb.precinct_name
ORDER BY pb.precinct_id;

-- If all 11 rows in precinct_boundaries have matches in dcp_precinct_boundaries,
-- then precinct_boundaries is SAFE TO DROP

-- ============================================
-- 3. REGULATORY_REFS_CORE vs REGULATORY_REFS
-- Is core a subset?
-- ============================================

-- Compare counts
SELECT 'regulatory_refs' as table_name, COUNT(*) as rows FROM regulatory_refs
UNION ALL
SELECT 'regulatory_refs_core', COUNT(*) FROM regulatory_refs_core;

-- Check if all core refs exist in main table
SELECT
  (SELECT COUNT(*) FROM regulatory_refs_core) as core_count,
  (SELECT COUNT(*)
   FROM regulatory_refs_core rrc
   WHERE EXISTS (
     SELECT 1 FROM regulatory_refs rr
     WHERE rr.document_id = rrc.document_id
       AND rr.ref_type = rrc.ref_type
       AND rr.ref_number = rrc.ref_number
   )
  ) as matches_in_main;

-- If matches_in_main = core_count, then regulatory_refs_core is a SUBSET
-- and SAFE TO DROP

-- Sample comparison
SELECT
  rrc.id as core_id,
  rrc.document_id,
  rrc.ref_type,
  rr.id as main_id
FROM regulatory_refs_core rrc
LEFT JOIN regulatory_refs rr
  ON rrc.document_id = rr.document_id
  AND rrc.ref_type = rr.ref_type
  AND rrc.ref_number = rr.ref_number
LIMIT 20;

-- ============================================
-- 4. DEVELOPMENT_PATHWAYS - Is it used?
-- ============================================

-- Check what's in it
SELECT * FROM development_pathways;

-- Check if any code references the pathway data
-- (You'd need to grep the codebase for 'development_pathways')
-- If it only has 1 row and looks like test data, likely SAFE TO DROP

-- ============================================
-- 5. TABLES WITH 0 ROWS BUT SIZE > 0
-- Why do they have size?
-- ============================================

-- Check dead tuples and last vacuum
SELECT
  schemaname,
  relname,
  n_live_tup as live_rows,
  n_dead_tup as dead_rows,
  last_vacuum,
  last_autovacuum,
  pg_size_pretty(pg_total_relation_size(schemaname || '.' || relname)) as size
FROM pg_stat_user_tables
WHERE n_live_tup = 0 AND pg_total_relation_size(schemaname || '.' || relname) > 8192
ORDER BY pg_total_relation_size(schemaname || '.' || relname) DESC;

-- ============================================
-- 6. BACKUP TABLES - FINAL CHECK BEFORE DROP
-- ============================================

-- Verify backup tables match expected counts
SELECT
  'dcp_general_provisions_backup_r1_fix' as tbl,
  COUNT(*) as rows,
  'Expected: 130' as expected
FROM dcp_general_provisions_backup_r1_fix
UNION ALL
SELECT 'dcp_general_provisions_corrupted_f1_backup', COUNT(*), 'Expected: 7'
FROM dcp_general_provisions_corrupted_f1_backup
UNION ALL
SELECT 'dcp_general_requirements_backup_20251030', COUNT(*), 'Expected: 555'
FROM dcp_general_requirements_backup_20251030
UNION ALL
SELECT 'dcp_general_requirements_old_broad_linking', COUNT(*), 'Expected: 189'
FROM dcp_general_requirements_old_broad_linking
UNION ALL
SELECT 'dcp_precinct_boundaries_backup_20251109_152059', COUNT(*), 'Expected: 85'
FROM dcp_precinct_boundaries_backup_20251109_152059
UNION ALL
SELECT 'dcp_precinct_boundaries_backup_polygon', COUNT(*), 'Expected: 46'
FROM dcp_precinct_boundaries_backup_polygon
UNION ALL
SELECT 'dcp_precinct_boundaries_backup_rename_20251109_153810', COUNT(*), 'Expected: 5'
FROM dcp_precinct_boundaries_backup_rename_20251109_153810
UNION ALL
SELECT 'dcp_precinct_requirements_backup_page_fix', COUNT(*), 'Expected: 265'
FROM dcp_precinct_requirements_backup_page_fix
UNION ALL
SELECT 'document_id_backup', COUNT(*), 'Expected: 47818'
FROM document_id_backup;

-- ============================================
-- 7. GENERATE DROP STATEMENTS
-- (Run after verifying above queries)
-- ============================================

-- PHASE 1: Drop backup tables (SAFE)
/*
DROP TABLE IF EXISTS dcp_general_provisions_backup_r1_fix;
DROP TABLE IF EXISTS dcp_general_provisions_corrupted_f1_backup;
DROP TABLE IF EXISTS dcp_general_requirements_backup_20251030;
DROP TABLE IF EXISTS dcp_general_requirements_old_broad_linking;
DROP TABLE IF EXISTS dcp_precinct_boundaries_backup_20251109_152059;
DROP TABLE IF EXISTS dcp_precinct_boundaries_backup_polygon;
DROP TABLE IF EXISTS dcp_precinct_boundaries_backup_rename_20251109_153810;
DROP TABLE IF EXISTS dcp_precinct_requirements_backup_page_fix;
DROP TABLE IF EXISTS document_id_backup;
*/

-- PHASE 2: Drop empty unused tables (SAFE)
/*
DROP TABLE IF EXISTS categorization_validation;
DROP TABLE IF EXISTS dcp_base_requirements;
DROP TABLE IF EXISTS dcp_precinct_metadata;
DROP TABLE IF EXISTS provision_diagrams;
DROP TABLE IF EXISTS requirement_metrics;
DROP TABLE IF EXISTS requirement_review_queue;
*/

-- PHASE 3: Drop after investigation confirms (RUN QUERIES ABOVE FIRST)
/*
DROP TABLE IF EXISTS precinct_boundaries;  -- Only if covered by dcp_precinct_boundaries
DROP TABLE IF EXISTS regulatory_refs_core;  -- Only if subset of regulatory_refs
DROP TABLE IF EXISTS development_pathways;  -- Only if unused/test data
*/

-- PHASE 4: Reclaim space
/*
VACUUM FULL;
*/

-- ============================================
-- 8. VERIFY SPACE RECOVERED (run after drops)
-- ============================================
-- Re-run query #1 to compare before/after size
