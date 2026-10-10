-- 097: cross-review corrections to rows added by 095 (gpt-5.6-sol, 2026-10-10). By row id.
--
-- 1. Canada Bay secondary dwelling landscaping (1490): 35% of the parent lot, but 40% in the
--    Biodiversity Corridor. Storing 35 overstates the footprint on a corridor lot (the
--    second-limb class of 093/094) -> NO FIGURE with the DCP's words.
-- 2. Ryde dual occupancy (1501-1504): the quoted Part 3.3 governs dual occupancy (ATTACHED) only
--    ("New Dual occupancy (attached) buildings are to meet the controls for new dwelling
--    houses"), while Ryde LEP 2014 permits dual occupancies of both kinds in R2-R4 and
--    dcp_setback_controls has no attached/detached split. Serving them would apply attached
--    rules to detached proposals -> retired (is_current FALSE, never deleted) until the
--    detached controls are found. DQ-142 rises by the 4 pairs this reopens.
-- 3. Northern Beaches dual occupancy front/rear (1514, 1515): the applicability quote began at
--    "Part D Design", so it did not show that Part B (where B7/B9 sit) applies. Replaced with
--    the sentence's run that names Part B, verbatim from Warringah DCP 2011 p253 (G10.1).
-- VERIFY: python scripts/dq_probe_live.py --id DQ-142   (29 -> 33)

BEGIN;

UPDATE dcp_setback_controls
   SET value_min = NULL, unit = NULL,
       condition = 'NO FIGURE: 35% of the parent lot site area, or 40% in the Biodiversity Corridor; also 50% of the front and rear setbacks landscaped'
 WHERE id = 1490 AND lga = 'canada_bay' AND dev_type = 'secondary_dwelling' AND control_type = 'landscaping_min'
   AND is_current AND extraction_method = 'manual_curation';

UPDATE dcp_setback_controls SET is_current = FALSE
 WHERE id IN (1501, 1502, 1503, 1504) AND lga = 'ryde' AND dev_type = 'dual_occupancy'
   AND is_current AND extraction_method = 'manual_curation';

UPDATE dcp_setback_controls
   SET source_text = replace(source_text,
         'Part D Design of this DCP apply and are be considered for dual occupancy and semi-detached dwelling development',
         'All controls such as those relating to subdivision, building setbacks, building design, landscaped open space, and amenity in Part B Built Form Controls, Part C Siting Factors, and Part D Design of this DCP apply and are be considered for dual occupancy and semi-detached dwelling development')
 WHERE id IN (1514, 1515) AND lga = 'northern_beaches' AND is_current AND extraction_method = 'manual_curation';

DO $$
DECLARE a integer; b integer; c integer;
BEGIN
    SELECT count(*) INTO a FROM dcp_setback_controls WHERE id = 1490 AND is_current AND value_min IS NULL AND condition LIKE 'NO FIGURE:%';
    SELECT count(*) INTO b FROM dcp_setback_controls WHERE id IN (1501, 1502, 1503, 1504) AND is_current;
    SELECT count(*) INTO c FROM dcp_setback_controls WHERE id IN (1514, 1515) AND is_current AND source_text LIKE '%Part B Built Form Controls%';
    IF a <> 1 OR b <> 0 OR c <> 2 THEN
        RAISE EXCEPTION '097: expected 1 / 0 / 2, got % / % / %', a, b, c;
    END IF;
END $$;

COMMIT;
