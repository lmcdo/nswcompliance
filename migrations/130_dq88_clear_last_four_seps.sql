-- 130: clear the DQ-88 review flag on the last four SEPPs (2026-11-25).
--
-- WHY: after migrations 128 and 129 four SEPPs stayed flagged: Exempt and Complying Development Codes, Industry and
-- Employment, Transport and Infrastructure, Biodiversity and Conservation. Every stored current row was checked for an
-- 8-word run that was in the old law and is nowhere in the whole instrument in force today. By hand and by the
-- scripts/dq88_apply_law_refresh.py plans (data/dq88_law_refresh_plan*_2026-11-25.json) every SERVED row holding
-- removed wording was either replaced with today's text word for word (proved in the same transaction, migration 113)
-- or retired: 25 + 14 served rows. The unserved rows the strict method could place (42) were done too.
--
-- LEFT, recorded in DQ-88: about 52 stored rows that are not served (v2_is_actionable false) still hold wording the
-- law has removed and could not be placed safely. Nobody is shown them; they are for the next re-extraction.
-- RUN FIRST: scripts/dq88_apply_law_refresh.py with plan2 and plan3 (the guard below checks the flagged count and that row 37984 is refreshed).
-- VERIFY: python scripts/dq_probe_live.py --id DQ-88   (4 -> 0)

BEGIN;

DO $$
DECLARE n integer;
BEGIN
    SELECT count(*) INTO n FROM regulatory_provisions WHERE id = 37984 AND is_current AND provision_text LIKE '3BA.11 Setbacks from protected trees%';
    IF n <> 1 THEN
        RAISE EXCEPTION '130: row 37984 has not been refreshed -- apply data/dq88_law_refresh_plan2_2026-11-25.json first';
    END IF;
    SELECT count(*) INTO n FROM instrument_registry WHERE is_active AND needs_review AND check_failures = 0;
    IF n <> 4 THEN
        RAISE EXCEPTION '130: expected the 4 flagged SEPPs after migration 129, found %', n;
    END IF;
END $$;

UPDATE instrument_registry
   SET needs_review = FALSE,
       notes = COALESCE(notes || ' ', '') || 'Reviewed 2026-11-25 (DQ-88, migration 130): every served row holding removed wording was replaced with the law in force or retired; see the migration header.'
 WHERE is_active AND needs_review
   AND version_date::date <= DATE '2026-11-25'
   AND instrument_key IN ('sepp_exempt_complying_2008', 'sepp_industry_employment_2021', 'sepp_transport_infrastructure_2021', 'sepp_biodiversity_conservation_2021');

DO $$
DECLARE n integer;
BEGIN
    SELECT count(*) INTO n FROM instrument_registry WHERE is_active AND needs_review AND check_failures = 0;
    IF n <> 0 THEN
        RAISE EXCEPTION '130: expected no flagged instruments left, found %', n;
    END IF;
END $$;

COMMIT;
