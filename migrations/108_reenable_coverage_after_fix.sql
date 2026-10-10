-- 108: switch back on the five coverage findings that were taken off 2026-10-10 while a bug was live.
-- RUN ONLY AFTER the constraint_arithmetic fix in this PR is deployed to the API (Railway).
--
-- The bug (#1255): when a coverage finding existed and a setback was missing, the arithmetic published
-- a buildable footprint with the missing setback counted as 0. Findings for pairs that hold some but not
-- all setbacks were exposed: Fairfield secondary dwelling (front), Burwood dual occupancy and secondary
-- dwelling, Sutherland dwelling house and dual occupancy (front is a NO FIGURE rule). They were set
-- is_current = FALSE so the live code took the safe generic path. The fix withholds the footprint
-- whenever any setback is missing, whatever the explanation text.
-- VERIFY after: python scripts/dq_probe_live.py --id DQ-142  (6 -> 1)

BEGIN;

UPDATE dcp_dev_type_coverage SET is_current = TRUE
 WHERE NOT is_current
   AND (council, dev_type, COALESCE(control_type, '')) IN (
     ('fairfield', 'secondary_dwelling', 'front_setback'),
     ('sutherland_shire', 'dwelling_house', 'cap'), ('sutherland_shire', 'dual_occupancy', 'cap'),
     ('burwood', 'secondary_dwelling', 'cap'), ('burwood', 'dual_occupancy', 'cap'));

DO $$
BEGIN
    IF (SELECT count(*) FROM dcp_dev_type_coverage WHERE NOT is_current) <> 0 THEN
        RAISE EXCEPTION '108: some findings are still off';
    END IF;
END $$;

COMMIT;
