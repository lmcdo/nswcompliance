-- 062_applicability_provenance.sql
--
-- WHY
-- ---
-- `v2_applicable_zones = ['ALL']` has meant two irreconcilable things:
--   (a) a structural config decided this rule applies to every zone, and
--   (b) no config matched, so the tagger defaulted.
-- Both wrote the identical value. Measured on production 2026-08-01: 19,072 of
-- 19,957 SERVED provisions (95.6%) carry ALL for both zones and dev types, so
-- "is this tag correct?" was unanswerable from the data for almost everything
-- being served. Not necessarily wrong — unauditable, which is worse, because it
-- cannot be checked and therefore cannot be fixed.
--
-- These two columns record WHICH of those happened. Same three-state discipline
-- as scripts/validate_zone_code_validity.py and validate_schema_contract.py:
-- "could not determine" must be visibly distinct from "determined".
--
-- SAFETY
-- ------
-- Purely additive: two nullable columns plus a CHECK. No existing column is
-- altered, no row is rewritten, nothing is dropped. Existing rows keep NULL.
--
-- NULL IS MEANINGFUL AND IS NOT A PASS
-- ------------------------------------
-- NULL = "tagged before provenance existed; the ALL is of unknown origin". It is
-- the honest state for the ~19k rows already in the table, and it is deliberately
-- NOT backfilled: re-deriving the source without re-running the tagger would be
-- inventing the very fact this column exists to record. It becomes non-NULL only
-- when a row is genuinely re-tagged.
--
-- The vocabulary is mirrored in enrichment/extractors/applicability_tagger.py
-- (APPLICABILITY_SOURCES); the CHECK below is what stops the two drifting, the
-- same way control_type_vocabulary.py is backed by a CHECK on dcp_setback_controls.

ALTER TABLE regulatory_provisions
  ADD COLUMN IF NOT EXISTS v2_zone_source     TEXT,
  ADD COLUMN IF NOT EXISTS v2_dev_type_source TEXT;

DO $$
BEGIN
  -- Scoped to this table, not just the name: pg_constraint.conname is unique per
  -- (table, name), not globally, so a same-named constraint on any other relation
  -- would make this re-run skip the CHECK and silently leave the column ungated.
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'regulatory_provisions_applicability_source_check'
      AND conrelid = 'public.regulatory_provisions'::regclass
  ) THEN
    ALTER TABLE regulatory_provisions
      ADD CONSTRAINT regulatory_provisions_applicability_source_check
      CHECK (
        (v2_zone_source IS NULL OR v2_zone_source IN (
          'config_specific','config_all','config_silent','no_config',
          'text_regex','filtered_to_all','no_document_id'))
        AND
        (v2_dev_type_source IS NULL OR v2_dev_type_source IN (
          'config_specific','config_all','config_silent','no_config',
          'text_regex','filtered_to_all','no_document_id'))
      );
  END IF;
END $$;

COMMENT ON COLUMN regulatory_provisions.v2_zone_source IS
  'Why v2_applicable_zones holds what it does. NULL = tagged before provenance '
  'existed (origin unknown, NOT a pass). Trustworthy assertions: config_specific, '
  'config_all, text_regex. Undetermined: config_silent, no_config, no_document_id, '
  'filtered_to_all.';

COMMENT ON COLUMN regulatory_provisions.v2_dev_type_source IS
  'Why v2_applicable_dev_types holds what it does. Same vocabulary as '
  'v2_zone_source.';

-- Reporting index: the whole point is asking "how much of what we serve is
-- undetermined?", which is a filtered scan over exactly these columns.
CREATE INDEX IF NOT EXISTS idx_regprov_applicability_source
  ON regulatory_provisions (v2_zone_source, v2_dev_type_source)
  WHERE is_current AND v2_is_actionable;
