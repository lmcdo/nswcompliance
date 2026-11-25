-- 128: clear the DQ-88 review flag on 12 LEPs, each with the evidence it was reviewed (2026-11-25).
--
-- WHY: the legislation monitor re-flagged 18 instruments after amendments dated 16 Oct to 13 Nov 2026.
-- Each was compared in a browser on legislation.nsw.gov.au (it refuses scripts from this PC): the paragraphs of the
-- in-force text on the baseline date versus today (the same method as scripts/law_change_diff.py).
-- Baselines: 2026-09-15 for inner_west, parramatta, the_hills; 2026-10-10 for the others; 2026-07-14 for wingecarribee.
--
-- CLEARED, and why (we store no LEP clause text that a change touched):
--   * We store each LEP's land use table (taken 2026-05-12; Wingecarribee 2026-07-14). No paragraph of any land
--     use table was removed or added in these 12. The changes are site-specific clauses, exempt development
--     and reclassification schedules, repealed clauses and amendment footnotes.
--   * Stored LEP-document rows holding a paragraph that the law removed: 6, none served (is_current and
--     v2_is_actionable false): 3 Inner West and 3 Industry and Employment SEPP rows that share standard wording.
--   * Inner West: only Schedule 1 item 54 (Callan Park additional permitted use) was added; no stored row mentions it.
--
-- NOT CLEARED (6): sepp_housing_2021, sepp_exempt_complying_2008, sepp_industry_employment_2021,
-- sepp_transport_infrastructure_2021, sepp_biodiversity_conservation_2021, sepp_planning_systems_2021:
-- 35 served rows hold wording the law has since changed (plan: ~/.claude/plans/ce-dq88-law-diff-RESUME-2026-11-25.md).
-- VERIFY: python scripts/dq_probe_live.py --id DQ-88   (18 -> 6)

BEGIN;

DO $$
DECLARE n integer;
BEGIN
    SELECT count(*) INTO n FROM instrument_registry WHERE is_active AND needs_review AND check_failures = 0;
    IF n <> 18 THEN
        RAISE EXCEPTION '128: expected exactly the 18 reviewed flags, found % (another instrument changed or was cleared since the review)', n;
    END IF;
END $$;

UPDATE instrument_registry
   SET needs_review = FALSE,
       notes = COALESCE(notes || ' ', '') || 'Reviewed 2026-11-25 (DQ-88, migration 128): paragraph diff of the in-force text against the baseline date; no land use table or stored clause text changed. See the migration header.'
 WHERE is_active AND needs_review
   -- Only the versions reviewed: a later amendment re-flags the instrument with a newer version_date.
   AND version_date::date <= DATE '2026-11-17'
   AND instrument_key IN (
     'inner_west_lep_2022', 'bayside_lep_2021', 'burwood_lep_2012', 'campbelltown_lep_2015',
     'canterbury_bankstown_lep_2023', 'liverpool_lep_2008', 'parramatta_lep_2023', 'penrith_lep_2010',
     'strathfield_lep_2012', 'the_hills_lep_2019', 'woollahra_lep_2014', 'wingecarribee_lep_2010');

DO $$
DECLARE n integer;
BEGIN
    SELECT count(*) INTO n FROM instrument_registry WHERE is_active AND needs_review AND check_failures = 0;
    IF n <> 6 THEN
        RAISE EXCEPTION '128: expected the 6 SEPPs still flagged, found %', n;
    END IF;
END $$;

COMMIT;
