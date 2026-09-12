-- 069_dcp_chapter_measurement.sql
--
-- One row per DCP chapter per measurement run: what four independent signals
-- found, and whether any of them could run at all.
--
-- WHY THIS EXISTS
-- ---------------
-- On 2026-09-12 a read-only audit of 270 chapters found 95 provably incomplete
-- and 984 listed sections not served. The number that mattered was neither of
-- those: 113 chapters -- 42% of the corpus -- could not be measured at all.
--
-- Nothing in the repo could answer "was this chapter ever complete", because the
-- only check that asked (ai_extractor.coverage_gap, #627, 2026-07-01) returned a
-- clean pass every time it failed to read the document, and did not store its
-- verdict anyway. Waverley's page map drifted 42 pages out of alignment, dropped
-- 11 parts and mislabelled 54 rows, and every re-extraction re-applied the same
-- broken map. No number moved. It was found because a person went looking.
--
-- A measurement that exists for a second and is discarded cannot be compared
-- against anything, and a defect nothing compares against is a defect nothing
-- finds. So the deliverable of this phase is not a verdict -- it is this table.
--
-- WHY NOT dcp_council_field_snapshot (migration 068)
-- --------------------------------------------------
-- Considered first, and rejected on grain and on content. That table is per
-- COUNCIL and holds {field_name: rows_populated} -- integer fill counts over the
-- served set. This one is per CHAPTER and holds verdicts, missing-code lists,
-- page-header disagreements and the source PDF's hash.
--
-- Forcing chapters into it would break the check that reads it:
-- check_council_completeness.py compares a council's newest row against its
-- previous one key by key, and would read chapter keys as watched fields and
-- report a dropped chapter as a dropped field. Diluting a check that works, to
-- avoid adding a table, is a worse trade than the table.
--
-- This is also not a fifth TRACKER. The four that must not become five are
-- status ledgers -- .claude/DATA_QUALITY_TRACKER.md, ce-CURRENT-AIM.md,
-- MEMORY.md/INDEX_*.md, GitHub issues -- all of which record what work is open.
-- This records a measurement, the same class as 068, and nothing reads it to
-- find out what to work on next.
--
-- WHY measured IS ITS OWN COLUMN
-- ------------------------------
-- `measured` is true when at least one signal that COULD have failed actually
-- ran. It is not "clean" and it is not derivable from the verdicts alone: a
-- chapter with no contents page and fewer than two section codes produces
-- NOT_MEASURED and TOO_FEW_CODES, which read like quiet passes and are not.
-- The whole reason this phase exists is that 42% of the corpus was reported fine
-- when it had not been read, so the distinction gets a column rather than a
-- convention.
--
-- WHY THE SIGNALS ARE COLUMNS AND NOT ONE JSONB
-- ---------------------------------------------
-- The opposite call to 068, and for the opposite reason. 068 chose JSONB because
-- its watched-field list is expected to GROW and the entire point is catching
-- fields nobody predicted. These four signals are a fixed, named set, each with
-- its own vocabulary of verdicts, and every one of them is queried directly --
-- "which chapters are mislabelled", "which are unmeasured". The variable-length
-- parts (missing codes, gap details, header examples) are JSONB; the verdicts
-- are not.
--
-- APPEND-ONLY
-- -----------
-- Every run inserts; nothing updates or deletes. The comparison is always "this
-- chapter's newest row versus its previous row", so history is the point. At ~270
-- chapters and a few hundred bytes each, a run is well under a megabyte.

BEGIN;

CREATE TABLE IF NOT EXISTS dcp_chapter_measurement (
  id                    BIGSERIAL PRIMARY KEY,
  measured_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  -- What caused this run: 'manual' (a human), 'monitor' (the scheduled sweep),
  -- 'commit' (dcp_commit_approved committed something). NOT named "trigger":
  -- TRIGGER is reserved in PostgreSQL and the column would need quoting at every
  -- call site forever after. Same choice, same reason, as 068.trigger_source.
  run_source            TEXT        NOT NULL,

  council               TEXT        NOT NULL,
  chapter_key           TEXT        NOT NULL,
  -- dcp_chapter_registry.content_hash at the moment of measurement. This is the
  -- column that ties a verdict to the document it was made about. Waverley's map
  -- survived a PDF version bump precisely because nothing held both halves.
  pdf_content_hash      TEXT,
  pdf_pages             INTEGER,
  live_rows             INTEGER     NOT NULL,

  -- TRUE when at least one signal that could have failed actually ran. FALSE is
  -- "still unknown", and is never the same as no findings.
  measured              BOOLEAN     NOT NULL,
  signals_run           SMALLINT    NOT NULL,

  -- signal 1: the source contents page vs the codes we serve.
  -- contents_status  READ | TITLES_ONLY | NO_CONTENTS | UNREADABLE | ERROR
  --   Only UNREADABLE is a defect in the parser. TITLES_ONLY means the contents
  --   page lists no codes at all (ashfield chapter-b), NO_CONTENTS means the
  --   document has none, which for a cover or a map is correct.
  -- contents_verdict OK | INCOMPLETE | VOCAB_MISMATCH | NO_ROWS | NOT_MEASURED:*
  --   VOCAB_MISMATCH is NOT a finding. Ashfield was once reported "15 of 15
  --   sections missing" when the contents says 10 and we store A10.
  contents_status       TEXT,
  contents_verdict      TEXT,
  listed_codes          INTEGER     NOT NULL DEFAULT 0,
  missing_codes         INTEGER     NOT NULL DEFAULT 0,
  missing_sample        JSONB       NOT NULL DEFAULT '[]'::jsonb,

  -- signal 2: holes in our OWN numbering. Needs no PDF, so it is the only signal
  -- with 100% coverage and the only reason "every chapter has a measured state"
  -- is reachable. TOO_FEW_CODES rather than NO_GAPS when a level carries fewer
  -- than two numbers: one number cannot disagree with itself, and a check that
  -- cannot fail must not report a pass.
  gap_verdict           TEXT,
  gap_count             INTEGER     NOT NULL DEFAULT 0,
  gap_sample            JSONB       NOT NULL DEFAULT '[]'::jsonb,

  -- signal 3: the part stamped on a row vs the running header of the page it was
  -- read from. The ONLY signal that sees MISLABELLED content -- waverley B15 is
  -- coded correctly and holds B17's text, and signals 1 and 2 both call that fine.
  header_verdict        TEXT,
  header_rows_checked   INTEGER     NOT NULL DEFAULT 0,
  header_rows_disagree  INTEGER     NOT NULL DEFAULT 0,
  header_examples       JSONB       NOT NULL DEFAULT '[]'::jsonb,

  -- signal 4: stored provision characters over the PDF's extractable characters.
  -- Needs neither a contents page nor numbering. capture_ratio is stored beside
  -- its own numerator and denominator so the verdict can be re-derived when the
  -- threshold moves -- the threshold is set from the corpus's measured
  -- distribution, not from any regulatory standard, and will move.
  capture_verdict       TEXT,
  capture_ratio         NUMERIC,
  pdf_text_chars        INTEGER,
  stored_chars          INTEGER
);

-- The read pattern: this chapter's most recent measurements, newest first.
CREATE INDEX IF NOT EXISTS idx_dcp_chapter_measurement_chapter
  ON dcp_chapter_measurement (council, chapter_key, measured_at DESC);

-- The other read pattern: one run's worth, for the ratchet and the report.
CREATE INDEX IF NOT EXISTS idx_dcp_chapter_measurement_run
  ON dcp_chapter_measurement (measured_at DESC);

COMMENT ON TABLE dcp_chapter_measurement IS
  'Per-chapter completeness measurement, four independent signals, one row per chapter per run. Append-only. Written by scripts/dcp_chapter_measure.py. measured=false means still unknown, never clean.';
COMMENT ON COLUMN dcp_chapter_measurement.measured IS
  'TRUE when at least one signal that could have failed actually ran. FALSE is "unknown", which is NOT "no findings" -- 42% of the corpus was reported fine on 2026-09-12 while unread.';
COMMENT ON COLUMN dcp_chapter_measurement.pdf_content_hash IS
  'dcp_chapter_registry.content_hash at measurement time. Ties a verdict to the document version it was made about; nothing held both halves when waverley''s page map drifted across a version bump.';
COMMENT ON COLUMN dcp_chapter_measurement.contents_verdict IS
  'VOCAB_MISMATCH is not a finding -- it means the contents codes and the stored codes are not the same kind of code (contents "10" vs stored "A10").';
COMMENT ON COLUMN dcp_chapter_measurement.header_rows_disagree IS
  'Rows whose stored part contradicts the running header of their own source page. The only signal that catches mislabelled (as opposed to absent) content.';
COMMENT ON COLUMN dcp_chapter_measurement.capture_ratio IS
  'stored_chars / pdf_text_chars. Corpus-relative, not a quality bar: DCP PDFs carry figures, tables and boilerplate that legitimately never become provisions.';

COMMIT;
