-- Migration: Perfect the SEPP/LEP/DCP VIEW filtering
-- Fixes the JOIN failures between regulatory_provisions and documents tables

-- PROBLEM:
-- regulatory_provisions.document_id = "State Environmental Planning Policy (Housing) 2021"
-- documents.id = "State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation"
-- They don't match! (spaces vs underscores)

-- SOLUTION: Pattern-based fallback VIEW
-- Uses JOIN when possible, falls back to pattern matching for edge cases

BEGIN;

CREATE OR REPLACE VIEW provisions_with_category AS
SELECT
    rp.*,
    COALESCE(
        d.document_type,  -- Use documents table when JOIN succeeds
        CASE              -- Fallback to pattern matching when JOIN fails
            WHEN rp.document_id LIKE '%State Environmental Planning Policy%'
              OR rp.document_id LIKE '%SEPP%'
              OR rp.document_id LIKE '%Housing%2021%'
              OR rp.document_id LIKE '%Transport%Infrastructure%2021%'
              OR rp.document_id LIKE '%Exempt%Complying%'
            THEN 'SEPP'

            WHEN rp.document_id LIKE '%Local Environmental Plan%'
              OR rp.document_id LIKE '%LEP%'
            THEN 'LEP'

            WHEN rp.document_id LIKE '%Development Control Plan%'
              OR rp.document_id LIKE '%DCP%'
            THEN 'DCP'

            ELSE 'OTHER'
        END
    ) as document_category
FROM regulatory_provisions rp
LEFT JOIN documents d ON rp.document_id = d.id;

-- Test the view
SELECT
    document_category,
    COUNT(*) as provision_count
FROM provisions_with_category
GROUP BY document_category
ORDER BY provision_count DESC;

-- Expected results:
--   DCP:   ~15,136 provisions
--   SEPP:  ~4,237 provisions (or more with fallback)
--   LEP:   ~5,910 provisions
--   OTHER: minimal (should be <100)

COMMIT;

-- Usage in API:
-- SELECT * FROM provisions_with_category WHERE document_category = 'SEPP';
-- SELECT * FROM provisions_with_category WHERE document_category = 'LEP';
-- SELECT * FROM provisions_with_category WHERE document_category = 'DCP';