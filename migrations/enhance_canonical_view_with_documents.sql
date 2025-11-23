-- =====================================================
-- Migration: Enhance regulatory_provisions_canonical VIEW
-- Date: 2025-10-12
-- Purpose: Add documents table JOIN to VIEW for document_type and lga access
--
-- WHY: Best practice for scalability/maintainability
-- - Single source of truth for canonical provisions
-- - DRY: JOIN logic in one place, not scattered across queries
-- - Backwards compatible: existing queries still work
-- - Future-proof: new document columns added in one place
-- =====================================================

-- Drop existing VIEW
DROP VIEW IF EXISTS regulatory_provisions_canonical;

-- Recreate VIEW with documents JOIN
-- This follows the "fat view" pattern for database abstraction
CREATE VIEW regulatory_provisions_canonical AS
SELECT
    rp.id,
    rp.document_id,
    rp.provision_type,
    rp.ref_number,
    rp.provision_text,
    rp.zone,
    rp.development_type,
    rp.page_number,
    rp.section_header,
    rp.text_level,
    rp.original_id,
    rp.created_at,
    rp.domain_classification,
    rp.classification_confidence,
    rp.cross_contamination_checked,
    rp.prp_k1_enhanced,
    rp.migration_id,
    rp.zone_confidence,
    rp.zone_inference_method,
    rp.full_text_length,
    rp.extraction_method,
    rp.last_updated,
    rp.is_canonical,
    rp.canonical_provision_id,
    rp.text_hash,
    rp.migration_phase,
    -- Add columns from documents table (only columns that exist)
    d.document_type,
    d.document_area,  -- Area/LGA information
    d.pdf_name,
    d.pdf_path,
    d.char_count,
    d.word_count
FROM regulatory_provisions rp
LEFT JOIN documents d ON rp.document_id = d.id
WHERE rp.is_canonical = TRUE;

-- Add comment explaining the VIEW design
COMMENT ON VIEW regulatory_provisions_canonical IS
'Canonical provisions with documents metadata.
This VIEW includes LEFT JOIN to documents table for direct access to document_type, lga, etc.
Best practice: All queries should use this VIEW instead of joining manually.
Maintains: Single source of truth, DRY principle, backwards compatibility.';

-- Verify the VIEW works
SELECT COUNT(*) as total_canonical_provisions FROM regulatory_provisions_canonical;

-- Test document_type and document_area columns are accessible
SELECT
    document_type,
    document_area,
    COUNT(*) as count
FROM regulatory_provisions_canonical
WHERE document_type IS NOT NULL
GROUP BY document_type, document_area
ORDER BY count DESC
LIMIT 10;
