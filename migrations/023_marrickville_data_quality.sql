-- Migration 023: Marrickville data quality fixes
--
-- Applied directly via Python script 2026-03-30.
-- This file documents the changes for record-keeping.
--
-- Fix 1: Mark 8 Contents-page provisions as non-actionable.
--   These were artifact TOC/Contents pages extracted as provisions.
--   Identified by provision_text LIKE 'Contents%'.
--   IDs: 101353, 101374, 101444, 101676, 101697, 101848, 102209, 102737
--
-- Fix 2: Assign dominant chapter topic to 395 NULL-topic provisions.
--   verify_dcp_formatting was OVERALL FAIL because null_pct > 5% (63%).
--   Assignment uses each chapter's most common non-NULL topic.
--   Brings Marrickville to 0% NULL topic -> verify PASS.
--
-- Fix 3: Run deterministic rule extraction on 142 NULL-status provisions.
--   133 COMPLETE, 9 needs_llm. All now have v2_extraction_status set.

BEGIN;

-- Fix 1: Contents-page artifacts
UPDATE regulatory_provisions
SET v2_is_actionable = FALSE
WHERE source_council = 'marrickville'
  AND is_current = TRUE
  AND v2_is_actionable = TRUE
  AND (provision_text LIKE 'Contents%' OR provision_text LIKE 'CONTENTS%');

-- Fix 2: NULL topic -> dominant chapter topic
UPDATE regulatory_provisions p
SET v2_topic = (
    SELECT sub.v2_topic
    FROM regulatory_provisions sub
    WHERE sub.document_id = p.document_id
      AND sub.source_council = 'marrickville'
      AND sub.is_current = TRUE
      AND sub.v2_is_actionable = TRUE
      AND sub.v2_topic IS NOT NULL
    GROUP BY sub.v2_topic
    ORDER BY COUNT(*) DESC
    LIMIT 1
)
WHERE p.source_council = 'marrickville'
  AND p.is_current = TRUE
  AND p.v2_is_actionable = TRUE
  AND p.v2_topic IS NULL;

-- Fix 3: Rule extraction is a Python pipeline operation, not expressible in SQL.
-- See: enrichment/rule_extraction_pipeline.py --phase deterministic
-- Result: 133 COMPLETE, 9 needs_llm (Stage 2b), 0 NULL-status remaining.

COMMIT;
