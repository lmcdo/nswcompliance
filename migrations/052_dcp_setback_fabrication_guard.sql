-- ============================================================
-- 052 — DCP setback fabrication guard (database-level chokepoint)
-- ============================================================
-- WHY: dcp_setback_controls is written by ~40 per-council insert scripts, 3
-- extractors, the review loop and ad-hoc SQL. An app-level gate (assert_clean_row)
-- only protects the doors that remember to call it. This CHECK constraint sits
-- UNDER all of them: any writer — script, extractor, manual INSERT/UPDATE — is
-- blocked from storing a value it admits is assumed/guessed. Single enforcement
-- point, cannot be bypassed.
--
-- WHAT IT BLOCKS: a *current* row (is_current = TRUE) that stores a value
-- (value_min or value_max) while a marker field confesses the value is assumed —
-- either review_reason = 'standard_pattern_assumed' or the condition text matches
-- the known "assumed standard NSW" / "standard NSW pattern" phrasing.
--
-- WHAT IT DOES NOT BLOCK (deliberately):
--   * Quarantined history: is_current = FALSE rows keep their old value (so the
--     audit trail / reversibility is preserved). Only LIVE rows must be clean.
--   * The honest "rule exists, value unknown" state: value_min/value_max = NULL
--     with an explanatory note is allowed.
--   * Mislabelled or SILENT guesses (a number scraped from the wrong clause with
--     no "assumed" tag) — those have no DB-detectable marker and are handled by
--     the validator sweep (scripts/validate_dcp_setbacks.py) + human review, not
--     this constraint.
--
-- SAFETY: added NOT VALID so it enforces on all NEW writes immediately WITHOUT a
-- full-table scan/lock and without failing on any legacy straggler. Run the
-- pre-check below; once it returns 0, VALIDATE to confirm existing live rows are
-- clean too. Reversible: DROP CONSTRAINT.

-- ── Pre-check: must return 0 before VALIDATE ────────────────────────────────
-- SELECT count(*) FROM dcp_setback_controls
-- WHERE is_current = TRUE
--   AND (value_min IS NOT NULL OR value_max IS NOT NULL)
--   AND (review_reason = 'standard_pattern_assumed'
--        OR condition ~* 'assumed standard|standard nsw pattern|assumed[^.]{0,30}pattern');

BEGIN;

ALTER TABLE dcp_setback_controls
  ADD CONSTRAINT dcp_setback_no_fabricated_value
  CHECK (
    NOT (
      is_current = TRUE
      AND (value_min IS NOT NULL OR value_max IS NOT NULL)
      AND (
        review_reason = 'standard_pattern_assumed'
        OR condition ~* 'assumed standard|standard nsw pattern|assumed[^.]{0,30}pattern'
      )
    )
  )
  NOT VALID;

COMMIT;

-- After the pre-check returns 0, run separately (brief ACCESS EXCLUSIVE lock):
--   ALTER TABLE dcp_setback_controls VALIDATE CONSTRAINT dcp_setback_no_fabricated_value;
--
-- Rollback:
--   ALTER TABLE dcp_setback_controls DROP CONSTRAINT dcp_setback_no_fabricated_value;
