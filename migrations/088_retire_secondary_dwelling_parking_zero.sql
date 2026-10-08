-- 088: retire housing_sepp_standards id 35, the secondary-dwelling "0 parking
-- spaces per dwelling" row. This is the "later migration" 084 promised for it.
--
-- WHY
-- id 35 states secondary_dwelling / parking_per_dwelling = 0 spaces, citing
-- "Part 3, Division 2". The SEPP (Housing) 2021 has no numeric parking standard
-- for a secondary dwelling. 084 (verified against the version in force from
-- 11 September 2026) recorded what the law actually says, one row per pathway:
--   id 56  cdc  Sch 1 cl 2(3)  "Nothing in this Schedule requires the provision
--                               of additional parking spaces ..."
--   id 59  da   s 53(2)(b)     the number of spaces on the site stays the same
--                               as it was immediately before the development.
-- Neither of those is "0 per dwelling" -- the DA rule keeps the existing spaces.
-- A zero standing in for an absence. id 35 is the last row DQ-136 counts and no
-- quote can clear it: provenance_check.py requires the value to appear in the
-- clause's words, and no clause contains it.
--
-- WHAT CHANGES FOR A READER (traced 2026-10-09)
--   services/constraint_arithmetic.py Step 10: for a secondary dwelling with no
--     DCP car_parking rate, parking_spaces_required was 0.0 sourced to id 35.
--     It is now absent, not zero. The DCP-rate branch is unchanged.
--   frontend-nextjs/app/api/compliance/parking: returns its existing
--     "Refer to DCP parking requirements" answer for secondary_dwelling. No
--     page, component or hook calls this route.
--   Path-specific readers (services/secondary_dwelling_paths.py) read 56/59 and
--     never read id 35. scripts/conveyancing_db.fetch_sepp_housing_standards
--     filters approval_pathway IS NULL, so 56/59 do not replace it there.
--
-- NOT RETIRED HERE: ids 34 and 44, which 084 also flagged. Both now carry the
-- quote of the clause that holds their number and pass DQ-136; whether their
-- pathway-agnostic framing is still needed is a separate question.
--
-- BACKUP + RESTORE: data/db_rollback_backups/housing_sepp_id35_pre_088_2026-10-09.json
-- holds the full row and the json_populate_record restore statement.
-- No foreign key references housing_sepp_standards (pg_constraint, 2026-10-09).
--
-- VERIFY
--   python scripts/dq_probe_live.py --id DQ-136    -- must read 0
--   and the assertion below, which refuses to commit unless exactly this row,
--   with exactly these values, went.

BEGIN;

DO $$
DECLARE
    n integer;
BEGIN
    DELETE FROM housing_sepp_standards
     WHERE id = 35
       AND development_type = 'secondary_dwelling'
       AND standard_type = 'parking_per_dwelling'
       AND numeric_value = 0
       AND approval_pathway IS NULL
       AND source_clause = 'Part 3, Division 2';
    GET DIAGNOSTICS n = ROW_COUNT;
    IF n <> 1 THEN
        RAISE EXCEPTION '088: expected to retire exactly 1 row (id 35), matched %', n;
    END IF;

    SELECT count(*) INTO n FROM housing_sepp_standards
     WHERE id IN (56, 59) AND source_quote IS NOT NULL AND source_quote <> '';
    IF n <> 2 THEN
        RAISE EXCEPTION '088: the rows that replace id 35 (56, 59) are not both quoted, found %', n;
    END IF;
END $$;

COMMIT;
