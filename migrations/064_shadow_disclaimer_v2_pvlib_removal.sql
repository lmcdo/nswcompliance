-- Migration 064: shadow disclaimer v2 — remove the pvlib attribution.
-- Date: 2026-08-06. Campaign: calibration Lane 1, decision D1.
--
-- WHY
-- `shadow-v1`.source_attributions opened with "pvlib solar position library
-- (NREL-backed, peer-reviewed)". pvlib has ZERO import sites anywhere in the
-- repo (`git grep -nE "^\s*(import|from)\s+pvlib"` returns nothing on
-- origin/main 0c41c09d); the only shadow library the running code imports is
-- pybdshadow (`services/shadow_model.py:92`, called at `:115`), which derives
-- the sun position itself from the modelled UTC instant. Naming a
-- "NREL-backed, peer-reviewed" library we do not run overstated the method
-- inside the record that exists to defend it.
--
-- Also corrected: the served `shadow_direction_deg` is a stored per-scenario
-- constant (`services/shadow_model.SHADOW_SCENARIOS`), not a per-report
-- calculation. v1 did not say so.
--
-- And v1's limitation (5) said scenarios are modelled "for Jun 21 and Sep 21
-- only" while SHADOW_SCENARIOS has modelled 21 December since it was written
-- (`dec21_12pm`) and the PDF names all three dates. The list below is taken
-- from SHADOW_SCENARIOS rather than copied forward: 21 Jun at 9am/noon/3pm,
-- 21 Sep at noon, 21 Dec at noon.
--
-- Nothing else in the shadow disclaimer changes, and no claim is upgraded —
-- v2 says strictly less about our method than v1 did.
--
-- LIFECYCLE (per migrations/042b + docs/qa/INDEX.md): insert the new version,
-- then stamp superseded_at on the old one. Rows are never deleted.
-- `services.audit_trail.get_current_disclaimer_version` selects the row with
-- superseded_at IS NULL, so new shadow reports record 'shadow-v2' from the
-- moment this runs. Existing report_audit_trail rows keep pointing at
-- 'shadow-v1' — that is the point of versioning, not a defect to repair.
--
-- EXPECTED ROW COUNTS
--   before: disclaimer_versions WHERE pipeline_name='shadow' -> 1 row
--           (id=4, version='shadow-v1', superseded_at IS NULL)
--   after:  2 rows; exactly one with superseded_at IS NULL, version='shadow-v2'

BEGIN;

INSERT INTO disclaimer_versions
    (pipeline_name, version, headline_disclaimer, limitations_text, source_attributions)
VALUES
('shadow', 'shadow-v2',
 'This report provides an indicative shadow analysis based on modelled building heights and modelled sun position. It is not a formal shadow study, ADG compliance assessment, or planning advice. The ADG solar access test result is based on modelled scenarios and may differ from a professional shadow analysis using measured building dimensions.',
 'Limitations: (1) Building heights are estimated from LEP height controls or spatial data — actual building heights may differ. (2) Shadow calculations assume flat terrain — sloping sites will produce different shadow patterns. (3) The pybdshadow model uses simplified building geometry (extruded footprints) — actual shadow patterns depend on roof form, setbacks, and architectural detail. (4) Construction change detection via Sentinel-2 spectral analysis operates at 10m resolution and is heuristic. (5) Five scenarios are modelled and no others: 21 June at 9am, noon and 3pm, 21 September at noon, and 21 December at noon — other dates and times of year are not assessed. (6) The compass direction reported for each scenario is a fixed value stored per scenario, not recalculated for the subject address, and has not been checked against published ephemeris.',
 'pybdshadow shadow casting (open source) — sun position is derived by pybdshadow from the modelled date and time. Element84 Earth Search Sentinel-2 L2A imagery (ESA Copernicus). NSW Planning Portal LEP height controls.');

UPDATE disclaimer_versions
   SET superseded_at = NOW()
 WHERE pipeline_name = 'shadow'
   AND version = 'shadow-v1'
   AND superseded_at IS NULL;

-- Fail the transaction rather than leave two live shadow disclaimers or none.
DO $$
DECLARE live_count INT;
BEGIN
    SELECT count(*) INTO live_count
      FROM disclaimer_versions
     WHERE pipeline_name = 'shadow' AND superseded_at IS NULL;
    IF live_count <> 1 THEN
        RAISE EXCEPTION
            'shadow disclaimer: expected exactly 1 live version after migration, found %',
            live_count;
    END IF;
END $$;

COMMIT;
