-- 129: clear the DQ-88 review flag on the Housing and Planning Systems SEPPs (2026-11-25).
--
-- WHY: after migration 128 (12 LEPs) six SEPPs stayed flagged. Each was compared with today's law: every stored
-- current row was checked for an 8-word run that was in the old law (the in-force text at the review baseline) and is
-- nowhere in the whole instrument in force today. Result for these two:
--   * sepp_housing_2021 (baseline 2026-09-15): 0 served rows hold removed wording. 2 stored rows that are not
--     served (v2_is_actionable false: ids 87505, 40539) still do; nobody is shown them.
--   * sepp_planning_systems_2021 (baseline 2026-10-10): its one served stale row (42041, s 2.6 submission counts) was
--     replaced with today's text, proved, by scripts/dq88_apply_law_refresh.py (PR 1707). 2 unserved rows still hold
--     removed wording.
--
-- NOT CLEARED (4): sepp_exempt_complying_2008, sepp_industry_employment_2021, sepp_transport_infrastructure_2021,
-- sepp_biodiversity_conservation_2021 -- 14 served rows could not be placed in today's text safely and need a person
-- (plan: ~/.claude/plans/ce-dq88-law-diff-RESUME-2026-11-25.md).
-- RUN FIRST: python scripts/dq88_apply_law_refresh.py --apply  (the guard below checks it)
-- VERIFY: python scripts/dq_probe_live.py --id DQ-88   (6 -> 4)

BEGIN;

DO $$
DECLARE n integer;
BEGIN
    -- 42041 must already carry today's wording (the old text had "other than" before the submission count)
    SELECT count(*) INTO n FROM regulatory_provisions WHERE id = 42041 AND is_current AND provision_text LIKE '%made in accordance with subsection (6A)%';
    IF n <> 1 THEN
        RAISE EXCEPTION '129: row 42041 has not been refreshed -- run scripts/dq88_apply_law_refresh.py --apply first';
    END IF;
    SELECT count(*) INTO n FROM instrument_registry WHERE is_active AND needs_review AND check_failures = 0;
    IF n <> 6 THEN
        RAISE EXCEPTION '129: expected the 6 flagged SEPPs after migration 128, found %', n;
    END IF;
END $$;

UPDATE instrument_registry
   SET needs_review = FALSE,
       notes = COALESCE(notes || ' ', '') || 'Reviewed 2026-11-25 (DQ-88, migration 129): no served stored row holds wording the law has removed; see the migration header.'
 WHERE is_active AND needs_review
   AND version_date::date <= DATE '2026-11-25'
   AND instrument_key IN ('sepp_housing_2021', 'sepp_planning_systems_2021');

DO $$
DECLARE n integer;
BEGIN
    SELECT count(*) INTO n FROM instrument_registry WHERE is_active AND needs_review AND check_failures = 0;
    IF n <> 4 THEN
        RAISE EXCEPTION '129: expected 4 SEPPs still flagged, found %', n;
    END IF;
END $$;

COMMIT;
