-- ============================================
-- DB CLEANUP - FINAL SCRIPT
-- Run in Supabase SQL Editor
-- Created: 2026-02-11
-- ============================================

-- ============================================
-- STEP 1: CHECK CURRENT STATE (run first)
-- ============================================

-- Current DB size
SELECT pg_size_pretty(pg_database_size(current_database())) as total_db_size;

-- Verify backup table counts match expected
SELECT
  'dcp_general_provisions_backup_r1_fix' as tbl, COUNT(*) as rows, 130 as expected FROM dcp_general_provisions_backup_r1_fix
UNION ALL SELECT 'dcp_general_provisions_corrupted_f1_backup', COUNT(*), 7 FROM dcp_general_provisions_corrupted_f1_backup
UNION ALL SELECT 'dcp_general_requirements_backup_20251030', COUNT(*), 555 FROM dcp_general_requirements_backup_20251030
UNION ALL SELECT 'dcp_general_requirements_old_broad_linking', COUNT(*), 189 FROM dcp_general_requirements_old_broad_linking
UNION ALL SELECT 'dcp_precinct_boundaries_backup_20251109_152059', COUNT(*), 85 FROM dcp_precinct_boundaries_backup_20251109_152059
UNION ALL SELECT 'dcp_precinct_boundaries_backup_polygon', COUNT(*), 46 FROM dcp_precinct_boundaries_backup_polygon
UNION ALL SELECT 'dcp_precinct_boundaries_backup_rename_20251109_153810', COUNT(*), 5 FROM dcp_precinct_boundaries_backup_rename_20251109_153810
UNION ALL SELECT 'dcp_precinct_requirements_backup_page_fix', COUNT(*), 265 FROM dcp_precinct_requirements_backup_page_fix
UNION ALL SELECT 'document_id_backup', COUNT(*), 47818 FROM document_id_backup;

-- Check precinct_boundaries overlap (should show all MATCH)
SELECT
  pb.precinct_id,
  pb.precinct_name,
  CASE WHEN dpb.precinct_id IS NOT NULL THEN 'MATCH' ELSE 'UNIQUE - KEEP' END as status
FROM precinct_boundaries pb
LEFT JOIN dcp_precinct_boundaries dpb
  ON pb.precinct_id = dpb.precinct_id OR pb.precinct_name = dpb.precinct_name;

-- Check regulatory_refs_core subset
SELECT
  (SELECT COUNT(*) FROM regulatory_refs_core) as core_rows,
  (SELECT COUNT(*) FROM regulatory_refs_core rrc
   WHERE EXISTS (
     SELECT 1 FROM regulatory_refs rr
     WHERE rr.document_id = rrc.document_id
       AND rr.ref_type = rrc.ref_type
       AND rr.ref_number = rrc.ref_number
   )) as found_in_main;

-- Check development_pathways (expect 1 row of test data)
SELECT * FROM development_pathways;


-- ============================================
-- STEP 2: DROP BACKUP TABLES (SAFE)
-- These are migration snapshots, no longer needed
-- ============================================

DROP TABLE IF EXISTS dcp_general_provisions_backup_r1_fix;
DROP TABLE IF EXISTS dcp_general_provisions_corrupted_f1_backup;
DROP TABLE IF EXISTS dcp_general_requirements_backup_20251030;
DROP TABLE IF EXISTS dcp_general_requirements_old_broad_linking;
DROP TABLE IF EXISTS dcp_precinct_boundaries_backup_20251109_152059;
DROP TABLE IF EXISTS dcp_precinct_boundaries_backup_polygon;
DROP TABLE IF EXISTS dcp_precinct_boundaries_backup_rename_20251109_153810;
DROP TABLE IF EXISTS dcp_precinct_requirements_backup_page_fix;
DROP TABLE IF EXISTS document_id_backup;


-- ============================================
-- STEP 3: DROP EMPTY UNUSED TABLES (SAFE)
-- Never populated, not referenced in code
-- ============================================

DROP TABLE IF EXISTS categorization_validation;
DROP TABLE IF EXISTS dcp_base_requirements;
DROP TABLE IF EXISTS dcp_precinct_metadata;
DROP TABLE IF EXISTS provision_diagrams;

-- NOTE: KEEPING requirement_metrics and requirement_review_queue
-- They're part of the feedback API (/api/feedback/requirement)
-- Empty because no users have submitted feedback yet, but functional


-- ============================================
-- STEP 4: DROP DUPLICATE/OBSOLETE TABLES
-- After confirming overlap in Step 1
-- ============================================

-- precinct_boundaries (11 rows) - duplicate of dcp_precinct_boundaries (90 rows)
DROP TABLE IF EXISTS precinct_boundaries;

-- regulatory_refs_core (762 rows) - subset of regulatory_refs (2698 rows)
DROP TABLE IF EXISTS regulatory_refs_core;

-- development_pathways (1 row) - test data, code references removed
DROP TABLE IF EXISTS development_pathways;


-- ============================================
-- STEP 5: RECLAIM DISK SPACE
-- ============================================

VACUUM FULL;


-- ============================================
-- STEP 6: VERIFY CLEANUP
-- ============================================

-- New DB size (should be smaller)
SELECT pg_size_pretty(pg_database_size(current_database())) as new_db_size;

-- Confirm tables are gone
SELECT tablename
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename LIKE '%backup%'
ORDER BY tablename;

-- Updated table count
SELECT COUNT(*) as remaining_tables
FROM pg_tables
WHERE schemaname = 'public';


-- ============================================
-- SUMMARY OF CHANGES
-- ============================================
/*
DROPPED (15 tables):
- dcp_general_provisions_backup_r1_fix (130 rows)
- dcp_general_provisions_corrupted_f1_backup (7 rows)
- dcp_general_requirements_backup_20251030 (555 rows)
- dcp_general_requirements_old_broad_linking (189 rows)
- dcp_precinct_boundaries_backup_20251109_152059 (85 rows)
- dcp_precinct_boundaries_backup_polygon (46 rows)
- dcp_precinct_boundaries_backup_rename_20251109_153810 (5 rows)
- dcp_precinct_requirements_backup_page_fix (265 rows)
- document_id_backup (47818 rows)
- categorization_validation (0 rows)
- dcp_base_requirements (0 rows)
- dcp_precinct_metadata (0 rows)
- provision_diagrams (0 rows)
- precinct_boundaries (11 rows - duplicate)
- regulatory_refs_core (762 rows - subset)
- development_pathways (1 row - test data)

KEPT (empty but functional):
- requirement_metrics (0 rows - feedback system)
- requirement_review_queue (0 rows - feedback system)

CODE CHANGES MADE:
- lib/database/client.ts - removed development_pathways query
- lib/database/postgres-client.ts - removed development_pathways query
- lib/database/mock-client.ts - removed development_pathways mock
- lib/precinct-service.ts - fixed comment reference

ESTIMATED SPACE SAVED: 5-10 MB
*/
