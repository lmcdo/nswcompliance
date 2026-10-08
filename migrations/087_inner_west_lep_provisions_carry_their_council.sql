-- 087: the Inner West LEP 2022 provisions carry their council instead of the
-- statewide marker.
--
-- WHY
-- `source_council IS NULL` means "statewide instrument" everywhere else in this
-- table: it is how the 5,303 SEPP provisions are distinguished from council
-- material, and it is what scripts/dq_probe_live.py's statewide probes and
-- app/api/sepp/parking-provisions/route.ts both test. Every Inner West LEP 2022
-- provision carried it. An LEP is a single council's instrument, so that is
-- simply wrong, and it is wrong in the direction that would serve one council's
-- planning controls to every property in NSW.
--
-- WHAT IS AND IS NOT AT RISK TODAY
-- Checked before writing, rather than assumed. The only serving endpoint that
-- reads `source_council IS NULL` is app/api/sepp/parking-provisions, and it also
-- pins `document_id` to the Housing SEPP, so an Inner West row could never match
-- it. app/api/lep/provisions finds these rows by a `document_id` prefix, not by
-- council, so it is unaffected either way. So nothing is mis-served right now;
-- this closes a trap rather than an incident. The next query written to mean
-- "statewide" would have inherited it.
--
-- WHICH SLUG, AND WHY NOT 'ashfield'
-- Inner West is a MERGED council. lga_registry holds slug 'inner_west'
-- (is_active, no parent) with 'ashfield', 'leichhardt' and 'marrickville' all
-- carrying parent_lga = 'inner_west'. The instrument is the Inner West LEP 2022,
-- which covers all three former areas, so the council is the parent slug and not
-- any one of the former councils -- those three slugs are in use on this table
-- for their own DCP material (ashfield 2,127, leichhardt 3,526,
-- marrickville 3,595 current rows) and must not be conflated with the LEP.
--
-- SCOPE: every row of the instrument, not only the served ones. source_council
-- records where a provision CAME FROM, which does not depend on whether it is
-- currently actionable. 554 are served (is_current AND v2_is_actionable); 1,683
-- are current but not actionable; 20 are not current. All 2,257 are Inner West
-- LEP rows and all get the council.
--
-- NOT FIXED HERE, recorded instead: 108 DCP provisions also sit on
-- source_council IS NULL. A DCP is likewise a single council's instrument, so
-- those are the same defect in a different corpus, but they span several councils
-- and need their council identified per row rather than by one instrument name.
-- Separate change.
--
-- VERIFY
--   SELECT count(*) FROM regulatory_provisions rp
--     JOIN documents d ON d.id = rp.document_id
--    WHERE d.document_type = 'LEP' AND rp.source_council IS NULL;   -- must be 0
--
-- RESTORE
--   UPDATE regulatory_provisions SET source_council = NULL
--    WHERE id = ANY(<ids captured in data/db_rollback_backups/>);

BEGIN;

-- Capture the non-LEP rows that ALREADY carry this council, before touching
-- anything, so the assertion below can test what THIS migration did rather than
-- an absolute. 16 such rows exist (14 Marrickville_DCP_2011, 2
-- Ashfield_DCP_2007, none served) -- a pre-existing inconsistency, since those
-- councils' own material uses the 'marrickville' and 'ashfield' slugs. Not
-- touched here, and recorded rather than silently absorbed. The first version of
-- this migration asserted zero and was correctly refused by its own guard.
CREATE TEMP TABLE _087_pre_existing ON COMMIT DROP AS
SELECT count(*) AS n
  FROM regulatory_provisions rp
  LEFT JOIN documents d ON d.id = rp.document_id
 WHERE rp.source_council = 'inner_west'
   AND coalesce(d.document_type, '') <> 'LEP';

UPDATE regulatory_provisions rp
   SET source_council = 'inner_west'
  FROM documents d
 WHERE d.id = rp.document_id
   AND d.document_type = 'LEP'
   AND d.pdf_name LIKE 'Inner West Local Environmental Plan 2022%'
   AND rp.source_council IS NULL;

DO $$
DECLARE
    still_null   integer;
    now_tagged   integer;
    wrong_type   integer;
    was_wrong    integer;
BEGIN
    -- No LEP provision may be left claiming to be a statewide instrument.
    SELECT count(*) INTO still_null
      FROM regulatory_provisions rp
      JOIN documents d ON d.id = rp.document_id
     WHERE d.document_type = 'LEP' AND rp.source_council IS NULL;
    IF still_null <> 0 THEN
        RAISE EXCEPTION 'still % LEP provision(s) with a null council', still_null;
    END IF;

    -- The council landed on the instrument's rows.
    SELECT count(*) INTO now_tagged
      FROM regulatory_provisions rp
      JOIN documents d ON d.id = rp.document_id
     WHERE d.document_type = 'LEP' AND rp.source_council = 'inner_west';
    IF now_tagged = 0 THEN
        RAISE EXCEPTION 'no LEP provision carries inner_west; the scope matched nothing';
    END IF;

    -- THIS migration must not have given the council to anything outside the
    -- instrument. Compared against the pre-existing count, not against zero.
    SELECT n INTO was_wrong FROM _087_pre_existing;
    SELECT count(*) INTO wrong_type
      FROM regulatory_provisions rp
      LEFT JOIN documents d ON d.id = rp.document_id
     WHERE rp.source_council = 'inner_west'
       AND coalesce(d.document_type, '') <> 'LEP';
    IF wrong_type <> was_wrong THEN
        RAISE EXCEPTION
            'inner_west landed on % non-LEP row(s); % pre-existed, so this migration added %',
            wrong_type, was_wrong, wrong_type - was_wrong;
    END IF;

    RAISE NOTICE 'Inner West LEP provisions carrying their council: %', now_tagged;
    RAISE NOTICE 'non-LEP rows on this council, unchanged at % (pre-existing, not fixed here)',
                 was_wrong;
END $$;

COMMIT;
