-- 091: four rear setbacks that were missing (DQ-139), each quoted from the
-- council's DCP text already stored in regulatory_provisions.
--
-- WHY: DQ-139 counts (council, development type) pairs with a front or side
-- setback but no rear one. The buildable-footprint arithmetic refuses to run
-- without it, so these pairs showed no figure. For these four the rear control
-- IS in the stored DCP text; it was never extracted into dcp_setback_controls.
-- Each quote below was found verbatim in the named regulatory_provisions row
-- (current, served) on 2026-10-10, and the chapter key / version / extraction
-- method are copied from the same pair's existing setback rows.
--
--   cumberland/dwelling_house      8 m            prov 104699 p8  (Part B 2.1, Table 1)
--   cumberland/secondary_dwelling  0.9 m (3 m 2 storeys) prov 104721 p25 (Part B 2.21, Table 5)
--   georges_river/secondary_dwelling 1.5 m        prov 127298 p14 (6.1.2.12 control 6)
--   parramatta/multi_dwelling_housing 6 m min, or 15% of site length if greater
--                                                 prov 105070 p81 (3.4.1.3 C.16)
--
-- Parramatta (greater of 6 m or 15% of site length) and Cumberland secondary
-- dwellings (0.9 m, 3 m for 2 storeys) store the MINIMUM in value_min with the
-- rest of the rule in `condition`, the convention the same councils' existing
-- side rows already use. The constraint arithmetic is an upper bound
-- ("indicative maximum envelope"), and the minimum setback keeps it one.
-- citation_status 'unjudged': the citation proof judges new rows on its next run.
-- VERIFY: python scripts/dq_probe_live.py --id DQ-139   (15 -> 11)
-- RESTORE: DELETE FROM dcp_setback_controls WHERE is_current AND control_type = 'rear_setback'
--   AND (lga, dev_type) IN (('cumberland','dwelling_house'),('cumberland','secondary_dwelling'),
--        ('georges_river','secondary_dwelling'),('parramatta','multi_dwelling_housing'));

BEGIN;

DO $$
DECLARE n integer;
BEGIN
    SELECT count(*) INTO n FROM dcp_setback_controls
     WHERE is_current AND control_type = 'rear_setback'
       AND (lga, dev_type) IN (('cumberland','dwelling_house'), ('cumberland','secondary_dwelling'),
                               ('georges_river','secondary_dwelling'), ('parramatta','multi_dwelling_housing'));
    IF n <> 0 THEN
        RAISE EXCEPTION '091: % of these rear setbacks already exist; not re-inserting', n;
    END IF;
END $$;

INSERT INTO dcp_setback_controls
  (lga, dev_type, control_type, value_min, value_max, unit, condition, applicability,
   source_text, section_ref, dcp_version, is_current, extraction_method, source_chapter_key,
   pdf_page, citation_status, needs_review)
VALUES
  ('cumberland', 'dwelling_house', 'rear_setback', 8, NULL, 'm', NULL, 'universal_residential',
   'Rear Setback Minimum 8m', 'cumberland-part-b-residential.pdf#dwelling_house', 'v1.0-baseline', TRUE,
   'manual_curation', 'cumberland-dcp-part-b-residential', 8, 'unjudged', FALSE),
  ('cumberland', 'secondary_dwelling', 'rear_setback', 0.9, NULL, 'm', '3m for 2 storeys', 'secondary_dwelling_specific',
   'Rear Setback Minimum 0.9m, 3m for 2 storeys', 'cumberland-part-b-residential.pdf#secondary_dwelling', 'v1.0-baseline', TRUE,
   'manual_curation', 'cumberland-dcp-part-b-residential', 25, 'unjudged', FALSE),
  ('georges_river', 'secondary_dwelling', 'rear_setback', 1.5, NULL, 'm', 'excluding laneways where a nil setback is permitted', 'universal_residential',
   'The minimum setback to side and rear boundaries is 1500mm, (excluding laneways where a nil setback is permitted).',
   '6.1.2.12 Control 6', 'Georges River DCP 2021 Amendment 6 (June 2024)', TRUE,
   'manual_curation', 'grdcp-part-6-1-low-density', 14, 'unjudged', FALSE),
  ('parramatta', 'multi_dwelling_housing', 'rear_setback', 6, NULL, 'm', 'or 15% of the site length, whichever is greater', 'universal_residential',
   'C.16 Development must provide a minimum rear setback equal to 15% of the site length or 6m, whichever is greater, as measured perpendicular to the rear boundary.',
   '3.4.1.3 C.16', 'Parramatta DCP 2023 Amendment 4', TRUE,
   'manual_curation', 'parramatta-dcp-2023-full', 81, 'unjudged', FALSE);

DO $$
DECLARE n integer;
BEGIN
    SELECT count(*) INTO n FROM dcp_setback_controls
     WHERE is_current AND control_type = 'rear_setback' AND source_text IS NOT NULL
       AND (lga, dev_type) IN (('cumberland','dwelling_house'), ('cumberland','secondary_dwelling'),
                               ('georges_river','secondary_dwelling'), ('parramatta','multi_dwelling_housing'));
    IF n <> 4 THEN
        RAISE EXCEPTION '091: expected 4 rows, found %', n;
    END IF;
END $$;

COMMIT;
