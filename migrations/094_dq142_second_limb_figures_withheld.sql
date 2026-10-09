-- 094: three more 092 rows whose stored figure is only one limb of the rule
-- (cross-review, gpt-5.6-sol, 2026-10-10 -- same class as 093 part 2). The
-- buildable-area sum uses value_min alone, so where the other limb can make the
-- control larger the footprint is overstated. Stored as NO FIGURE so the
-- footprint is withheld; the DCP's words stay in source_text.
--   1398 hornsby dual_occupancy front: 6 m, but 9 m to designated roads
--   1365 parramatta dual_occupancy side: 1.5 m, but buildings occupy at most 80% of lot width
--   1391 cumberland dual_occupancy landscaping: 20% of site, or 30 m2 per dwelling
-- VERIFY: python scripts/dq_probe_live.py --id DQ-142  (unchanged: NO FIGURE rows count as decided)

BEGIN;

UPDATE dcp_setback_controls SET value_min = NULL, condition = CASE id
    WHEN 1398 THEN 'NO FIGURE: 6 m to local roads and 9 m to designated roads; attached dual occupancy 7.6 m'
    WHEN 1365 THEN 'NO FIGURE: minimum 1.5 m, and buildings to occupy a maximum of 80% of the lot width'
    WHEN 1391 THEN 'NO FIGURE: minimum 20% of total site area or 30 m2 per dwelling'
  END
 WHERE is_current AND extraction_method = 'manual_curation'
   AND (id, lga, control_type) IN ((1398, 'hornsby', 'front_setback'), (1365, 'parramatta', 'side_setback'),
                                   (1391, 'cumberland', 'landscaping_min'));

DO $$
DECLARE n integer;
BEGIN
    SELECT count(*) INTO n FROM dcp_setback_controls
     WHERE id IN (1398, 1365, 1391) AND is_current AND value_min IS NULL AND condition LIKE 'NO FIGURE:%';
    IF n <> 3 THEN
        RAISE EXCEPTION '094: expected 3 rows withheld, got %', n;
    END IF;
END $$;

COMMIT;
