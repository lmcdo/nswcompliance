-- Rollback v2_heritage_type tagging to NULL
-- Use this if tagging results are incorrect

-- Check current state
SELECT
    'BEFORE ROLLBACK' as status,
    v2_heritage_type,
    COUNT(*) as count
FROM regulatory_provisions
WHERE v2_marker = 'heritage'
GROUP BY v2_heritage_type
ORDER BY count DESC;

-- Rollback: Set all heritage provisions back to NULL
-- UNCOMMENT TO EXECUTE:
-- UPDATE regulatory_provisions
-- SET v2_heritage_type = NULL
-- WHERE v2_marker = 'heritage';

-- Verify rollback
-- SELECT
--     'AFTER ROLLBACK' as status,
--     v2_heritage_type,
--     COUNT(*) as count
-- FROM regulatory_provisions
-- WHERE v2_marker = 'heritage'
-- GROUP BY v2_heritage_type;
