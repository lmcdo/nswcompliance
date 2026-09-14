-- 073: dcp_plan_as_at.currency_confirmed_plan -- WHICH plan a plan-in-force confirmation is about.
--
-- currency_confirmed_at records when a person confirmed a council's plan is the one in force, but not
-- which plan. The outreach gate (OC-17) joined it by council only, so a confirmation of one plan would
-- pass a council still serving numbers from another (cross-review of #1115, 2026-09-14; measured the same
-- day: waverley serves 7 numbers from Waverley DCP 2012 beside 42 from Waverley DCP 2022).
--
-- Holds the dcp_chapter_registry.dcp_name the person confirmed. Nullable, no default, no backfill: no
-- confirmation has been recorded yet (0 of 28 rows have currency_confirmed_at), so there is nothing to
-- carry over and nothing may be inferred. Set together with currency_confirmed_at, enforced below.

ALTER TABLE dcp_plan_as_at ADD COLUMN IF NOT EXISTS currency_confirmed_plan text;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conname = 'dcp_plan_as_at_confirmation_names_its_plan'
           AND conrelid = 'dcp_plan_as_at'::regclass
    ) THEN
        ALTER TABLE dcp_plan_as_at
            ADD CONSTRAINT dcp_plan_as_at_confirmation_names_its_plan
            CHECK ((currency_confirmed_at IS NULL) = (NULLIF(btrim(currency_confirmed_plan), '') IS NULL));
    END IF;
END
$$;

COMMENT ON COLUMN dcp_plan_as_at.currency_confirmed_plan IS
    'The dcp_chapter_registry.dcp_name a person confirmed, at currency_confirmed_at, as the plan in force for '
    'this council. Set together with currency_confirmed_at (CHECK dcp_plan_as_at_confirmation_names_its_plan). '
    'scripts/outreach_claim_checks.py (OC-17) counts a confirmation only when this equals the plan name of '
    'every chapter the council serves numbers from.';
