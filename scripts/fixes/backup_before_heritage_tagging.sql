-- Backup current v2_heritage_type state before tagging
-- Run this BEFORE running tag_heritage_type_supabase.py

-- Create backup table
CREATE TABLE IF NOT EXISTS v2_heritage_type_backup_20260212 AS
SELECT id, v2_heritage_type, v2_marker, document_id
FROM regulatory_provisions
WHERE v2_marker = 'heritage';

-- Verify backup
SELECT
    'Backup created' as status,
    COUNT(*) as total_provisions,
    COUNT(v2_heritage_type) FILTER (WHERE v2_heritage_type IS NOT NULL) as already_tagged
FROM v2_heritage_type_backup_20260212;

-- To rollback later (if needed):
-- UPDATE regulatory_provisions rp
-- SET v2_heritage_type = backup.v2_heritage_type
-- FROM v2_heritage_type_backup_20260212 backup
-- WHERE rp.id = backup.id;
