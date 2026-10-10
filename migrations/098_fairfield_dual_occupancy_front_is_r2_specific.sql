-- 098: row 1491 (fairfield dual_occupancy front_setback, added by 095) states its own zone:
-- "front setback must be within 1.5 m of the average existing front street setback (R2 zone)".
-- It was inserted as universal_residential, so the zone filter (which only examines
-- zone_specific rows) would serve it to every zone. DQ-32b caught it in CI on #1249.
-- VERIFY: python scripts/dq_probe_live.py --id DQ-32b  (0)

BEGIN;

UPDATE dcp_setback_controls SET applicability = 'zone_specific'
 WHERE id = 1491 AND lga = 'fairfield' AND dev_type = 'dual_occupancy' AND control_type = 'front_setback'
   AND is_current AND applicability = 'universal_residential' AND condition LIKE '%(R2 zone)%';

DO $$
BEGIN
    IF (SELECT count(*) FROM dcp_setback_controls WHERE id = 1491 AND applicability = 'zone_specific') <> 1 THEN
        RAISE EXCEPTION '098: row 1491 not tagged';
    END IF;
END $$;

COMMIT;
