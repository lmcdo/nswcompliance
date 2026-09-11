-- 068_council_field_snapshot.sql
--
-- Record what each council's served provisions CARRY, so the next commit can be
-- compared against it.
--
-- WHY THIS EXISTS
-- ---------------
-- On 2026-09-10 three bugs were fixed in one day (#1079, #1080, #1081). Each was
-- the same shape: a council update silently dropped a field -- a chapter sourced
-- from a repealed PDF, precinct keys wiped on every commit, zone codes NSW
-- retired in 2022. They were not three bugs. They were one hole appearing in
-- three fields, and the two that were caught were the only two that happened to
-- have a check watching them.
--
-- Ashfield fell to 118 precinct-keyed rows of 2,041 and Marrickville to 37 of
-- 2,403. From outside, that is a precinct lookup returning nothing. It was found
-- two months later because a person went looking, not because a number moved.
--
-- The fields nobody has thought to watch yet are the point. ref_number is 93%
-- filled on served rows and nothing in the repo knows what fills the other 7%.
-- A check that enumerates "phases that exist versus phases that run" cannot see
-- that class at all. A check that compares this council against this council
-- last time can.
--
-- WHY JSONB RATHER THAN A COLUMN PER FIELD
-- ----------------------------------------
-- The watched-field list is expected to grow, and the entire purpose of this
-- table is catching fields nobody predicted. Column-per-field makes adding the
-- next field a migration, which is the friction that ends with the field not
-- being watched at all. `counts` is {field_name: rows_populated}.
--
-- The consequence is handled in the checker, not here: a field ABSENT from an
-- older snapshot is "no baseline for that field", never "dropped to zero".
-- Absence of a measurement must never read as a measurement -- that is the same
-- failure direction as the "0% drift" self-comparison that left DQ-30 marked
-- Fixed while 286 rows carried retired zone codes.
--
-- WHAT THIS TABLE DELIBERATELY DOES NOT HOLD
-- ------------------------------------------
-- Zone validity. Measured 2026-09-11: v2_applicable_zones is populated on 100%
-- of served rows for every council, because the #1081 write guard falls back to
-- ['ALL'] when it cannot verify a code. A fill count on that column can never
-- move, so it would be a check that cannot fail. Zone health is asserted by
-- calling scripts/validate_zone_code_validity.py, which compares stored codes
-- against the live per-LGA land-use table and can.
--
-- APPEND-ONLY
-- -----------
-- Every recording inserts; nothing updates or deletes. The comparison is always
-- "this council's newest row versus its previous row", so history is the point.
-- Rows are a few hundred bytes and a recording happens at most a few times a day
-- (a commit run that changed something, plus a scheduled backstop).

BEGIN;

CREATE TABLE IF NOT EXISTS dcp_council_field_snapshot (
  id              BIGSERIAL PRIMARY KEY,
  taken_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  -- What caused this recording: 'commit' (dcp_commit_approved committed
  -- something), 'monitor' (the scheduled backstop), 'manual' (a human ran it).
  -- NOT named "trigger": TRIGGER is a reserved word in PostgreSQL, and the
  -- column would need quoting at every call site forever after.
  trigger_source  TEXT        NOT NULL,
  -- Councils are stored exactly as regulatory_provisions.source_council, with
  -- one exception: NULL becomes the sentinel below. Verified 2026-09-11 that
  -- ZERO served rows carry an empty-string source_council, so the sentinel
  -- cannot collide with a real value.
  council         TEXT        NOT NULL,
  -- Denominator: live + actionable rows for this council -- the SERVED set. It
  -- is stored beside the counts because a fill ratio computed against a
  -- different denominator than the one recorded is not a comparison.
  served          INTEGER     NOT NULL,
  -- {field_name: rows_where_populated}. See the header for why this is JSONB.
  counts          JSONB       NOT NULL
);

-- The only read pattern: this council's most recent recordings, newest first.
CREATE INDEX IF NOT EXISTS idx_council_field_snapshot_council_taken
  ON dcp_council_field_snapshot (council, taken_at DESC);

COMMENT ON TABLE dcp_council_field_snapshot IS
  'Per-council per-field fill counts over served provisions, recorded after a commit run and by a scheduled backstop. Append-only. Read by scripts/check_council_completeness.py, which alerts when a field goes backwards.';
COMMENT ON COLUMN dcp_council_field_snapshot.counts IS
  'JSONB {field_name: rows_populated}. A field missing from an older row means "not measured then" -- never zero.';
COMMENT ON COLUMN dcp_council_field_snapshot.council IS
  'source_council verbatim, or the sentinel used by check_council_completeness.py for the statewide (NULL source_council) set.';

COMMIT;
