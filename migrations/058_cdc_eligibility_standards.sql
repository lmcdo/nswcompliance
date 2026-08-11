-- CDC eligibility standards — DB home for the Codes SEPP values the CDC screen
-- checks against (issue #820, plan ce-cdc-screen-consolidation-2026-07).
--
-- Pattern: housing_sepp_standards (migration 045). Every row must cite the
-- regulatory_provisions rows it was extracted from (source_provision_ids) and
-- quote the operative text (source_quote) — the ingested SEPP (Exempt and
-- Complying Development Codes) 2008 corpus is the authority, never a code
-- constant. Consumers read ONLY manual_verified rows and fail closed when the
-- needed standards are absent (#684/#816/#819 pattern): no verified row, no
-- figure rendered.
--
-- Schema only — seeding is a separate, founder-reviewed step: rows land with
-- manual_verified = FALSE and are invisible to the engine until verified.
-- Additive; touches no existing table.

CREATE TABLE IF NOT EXISTS cdc_eligibility_standards (
  id                    serial PRIMARY KEY,
  -- Which complying-development code the standard belongs to, e.g.
  -- 'housing_code' (Part 3), 'low_rise_housing_diversity_code', 'inland_code'.
  code_name             text        NOT NULL,
  -- 'eligible_zones' | 'min_lot_size' | 'max_height' | 'acid_sulfate_max_class'
  -- | 'land_exclusion' | ... (vocabulary enforced in the loader, not a CHECK,
  -- so new standard types don't need a migration)
  standard_type         text        NOT NULL,
  numeric_value         numeric,
  text_value            text,
  applicable_zones      text[],
  -- Conditional applicability in the instrument's own words, e.g. cl
  -- 6.4(1)(d)(ii): the 200 m2 minimum applies only "if no minimum size is, or
  -- was at the relevant time, specified". NULL = unconditional.
  conditionality        text,
  ref_number            text,
  -- Provenance is ENFORCED, not aspirational: a standard with no cited
  -- provisions or a blank quote cannot exist (Sol review round 2).
  source_provision_ids  integer[]   NOT NULL CHECK (cardinality(source_provision_ids) > 0),
  source_quote          text        NOT NULL CHECK (btrim(source_quote) <> ''),
  effective_date        date,
  -- Lifecycle: superseded standards are retired by flipping is_active off,
  -- never deleted (audit trail). The partial unique index below guarantees at
  -- most ONE active row per (code_name, standard_type), so the loader can
  -- never pick nondeterministically between a superseded and a replacement
  -- value (Sol review of PR #824).
  is_active             boolean     NOT NULL DEFAULT TRUE,
  manual_verified       boolean     NOT NULL DEFAULT FALSE,
  verified_by           text,
  verified_at           timestamptz,
  created_at            timestamptz NOT NULL DEFAULT now()
  -- No unconditional UNIQUE on (code_name, standard_type, ref_number): an
  -- amended value under the SAME clause ref must be insertable alongside its
  -- retired predecessor (audit trail). The partial index below is the only
  -- uniqueness rule: one ACTIVE row per (code_name, standard_type).
);

CREATE UNIQUE INDEX IF NOT EXISTS cdc_standards_one_active
  ON cdc_eligibility_standards (code_name, standard_type)
  WHERE is_active;

COMMENT ON TABLE cdc_eligibility_standards IS
  'Codes SEPP 2008 complying-development standards, provenance-cited to regulatory_provisions. Consumers read manual_verified rows only and fail closed when absent (issue #820).';
