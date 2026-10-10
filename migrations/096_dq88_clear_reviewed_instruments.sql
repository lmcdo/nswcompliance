-- 096: clear DQ-88 review flags on 27 instruments, each with the evidence it was reviewed.
--
-- WHY: the legislation monitor was blind from 2026-06-08 to 2026-10-07 (PCO export format
-- change, fixed in #1237). Its first good run flagged every instrument that had changed since,
-- so DQ-88 read 30. Each was compared on 2026-10-10 with scripts/law_change_diff.py (in-force
-- text on legislation.nsw.gov.au at the date our data was taken vs today, from the Fly IP).
--
-- CLEARED, and why:
--   A. 6 reviewed 2026-09-15 against the 15 Sep text (recorded in their notes); their newest
--      version is dated 4-11 Sep 2026, before that review: sepp_housing_2021,
--      sepp_exempt_complying_2008, inner_west_lep_2022, parramatta_lep_2023,
--      sutherland_lep_2015, the_hills_lep_2019.
--   B. 18 LEPs whose clause text we do not store (zone/height/FSR come live from the Planning
--      Portal). Only lep_land_use_table is stored (taken 2026-05-12). 12 May -> today changed no
--      Land Use Table except Campbelltown's (an RE zone gained 4 uses; we hold no row for them),
--      and every stored Campbelltown and Cumberland residential/use row checked agrees with today's
--      text (Cumberland's 12 May version is PDF-only, so it was checked row by row instead).
--      Canterbury-Bankstown changed only cl 6.52B (one site) since its 15 Sep review.
--   C. sepp_resilience_hazards_2021: no change since the 4 Aug 2023 version our text is from.
--   D. sepp_primary_production_2021 (s 2.27 repealed) and sepp_sustainable_buildings_2022
--      (s 2.1(2A) inserted, s 4.2(2) repealed): stored text brought up to date by
--      scripts/dq88_refresh_2026_10_10.py -- RUN THAT FIRST (the assertion below checks it).
--
-- NOT CLEARED (3): sepp_biodiversity_conservation_2021, sepp_planning_systems_2021,
-- sepp_transport_infrastructure_2021 -- 425 stored rows (174 served) hold a sentence present in
-- the version our text is from and absent today. They need a clause-by-clause refresh.
-- VERIFY: python scripts/dq_probe_live.py --id DQ-88   (30 -> 3)

BEGIN;

DO $$
DECLARE n integer;
BEGIN
    SELECT count(*) INTO n FROM regulatory_provisions
     WHERE is_current AND provision_text ~ 'Consultation with Secretary of Department of Industry|until the end of 30 September 2024';
    IF n <> 0 THEN
        RAISE EXCEPTION '096: % current rows still hold repealed Primary Production / Sustainable Buildings text -- run scripts/dq88_refresh_2026_10_10.py --apply first', n;
    END IF;
END $$;

UPDATE instrument_registry
   SET needs_review = FALSE,
       notes = COALESCE(notes || ' ', '') || 'Reviewed 2026-10-10 (DQ-88, migration 096): point-in-time comparison against the version our data was taken from; see the migration header for the evidence.'
 WHERE is_active AND needs_review
   -- Only the version reviewed here: a later amendment re-flags the instrument with a newer
   -- version_date, and that new flag must not be cleared by this review (cross-review).
   AND version_date <= DATE '2026-10-10'
   AND instrument_key IN (
     'sepp_housing_2021', 'sepp_exempt_complying_2008', 'inner_west_lep_2022', 'parramatta_lep_2023',
     'sutherland_lep_2015', 'the_hills_lep_2019',
     'bayside_lep_2021', 'blacktown_lep_2015', 'burwood_lep_2012', 'campbelltown_lep_2015',
     'canada_bay_lep_2013', 'cumberland_lep_2021', 'fairfield_lep_2013', 'georges_river_lep_2021',
     'hornsby_lep_2013', 'liverpool_lep_2008', 'northern_beaches_lep_2014', 'penrith_lep_2010',
     'randwick_lep_2012', 'ryde_lep_2014', 'strathfield_lep_2012', 'waverley_lep_2012',
     'woollahra_lep_2014', 'canterbury_bankstown_lep_2023',
     'sepp_resilience_hazards_2021', 'sepp_primary_production_2021', 'sepp_sustainable_buildings_2022');

DO $$
DECLARE n integer;
BEGIN
    SELECT count(*) INTO n FROM instrument_registry WHERE is_active AND needs_review;
    IF n <> 3 THEN
        RAISE EXCEPTION '096: expected exactly the 3 unreviewed SEPPs still flagged, found % (a listed instrument changed again or failed its check -- review it before applying)', n;
    END IF;
END $$;

COMMIT;
