-- 089: retire housing_sepp_standards ids 34 and 44, the last two pathway-agnostic
-- granny-flat lot rows. Step 3 of the granny-flat correction begun in #1239.
--
-- APPLY ONLY AFTER the code that stops reading them is deployed (this PR): until
-- then services/granny_flat.py on production still gates on id 44.
--
-- WHY
--   id 44  min_lot_size  450 m2  "53(1)(b)"
--   id 34  min_lot_width 12 m    "Schedule 1, Part 2"
-- Both were read as one minimum for every granny flat. The SEPP (Housing) 2021
-- sets no such minimum (verified against the version in force from 11 Sep 2026,
-- recorded in 084):
--   - 450 m2 is s 53(2)(a): a NON-DISCRETIONARY site area for DETACHED granny
--     flats on the DA path; consent can still be granted below it (Act s 4.15(3)).
--   - 12 m is the lowest of three CDC road-frontage bands, Sch 1 cl 2(1)(b)
--     (12 / 15 / 18 m by lot area), not a lot width.
-- 084 stored those rules per clause and path (ids 53-61). This PR makes every
-- reader answer from them via services/secondary_dwelling_paths.assess(), and
-- every reader explicitly ignores ids 34/44 already -- so deleting them changes
-- no answer; it removes the last place a 450 m2 "minimum lot size" is stored.
--
-- id 35 (0 parking) was retired by 088 on feat/rule-scope-inventory.
--
-- BACKUP + RESTORE: data/db_rollback_backups/housing_sepp_ids34_44_pre_089_2026-10-09.json
-- No foreign key references housing_sepp_standards (pg_constraint, 2026-10-09).
--
-- VERIFY
--   SELECT count(*) FROM housing_sepp_standards WHERE id IN (34, 44);   -- 0
--   the assertions below, which refuse to commit unless exactly these two rows
--   went and the per-path rules that replace them are all still present.

BEGIN;

DO $$
DECLARE
    n integer;
BEGIN
    DELETE FROM housing_sepp_standards
     WHERE development_type = 'secondary_dwelling'
       AND approval_pathway IS NULL
       AND ((id = 44 AND standard_type = 'min_lot_size'  AND numeric_value = 450)
         OR (id = 34 AND standard_type = 'min_lot_width' AND numeric_value = 12));
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 2 THEN
        RAISE EXCEPTION '089: expected to retire exactly 2 rows (ids 34, 44), matched %', n;
    END IF;

    SELECT count(*) INTO n FROM housing_sepp_standards
     WHERE development_type = 'secondary_dwelling'
       AND approval_pathway IS NOT NULL
       AND source_quote IS NOT NULL AND source_quote <> '';
    IF n < 9 THEN
        RAISE EXCEPTION '089: only % quoted per-path granny-flat rules remain; expected the 9 from 084', n;
    END IF;
END $$;

COMMIT;
