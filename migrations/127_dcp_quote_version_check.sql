-- 127: per file version, is a control's quote printed word for word on the page the control cites?
--
-- WHY. dcp_setback_controls.quote_status (migration 119) answers this for the CURRENT council file only. The evidence page also lists the
-- earlier files we hold (dcp_source_versions, migration 126) and could only say "not checked". Checking a version means downloading its PDF,
-- too slow per request, so the verdicts are computed offline by scripts/dcp_quote_version_check.py --apply and read from here.
--
-- WHAT. One new table; no existing row or column changes. Verdicts use the same words and the same matcher as migration 119:
--   verbatim | wrong_page (the words are in that file but not on the cited page; an older file can repaginate) | not_found | no_source
-- quote_sha256 is the hash of the control's source_text when it was checked, so a reader can tell a verdict is stale if the quote changed.
-- Rows go when their control row is deleted (ON DELETE CASCADE). A control's page number comes from its own (current) file; for an older
-- file, wrong_page does not mean the control is wrong.

BEGIN;

CREATE TABLE IF NOT EXISTS dcp_quote_version_check (
    control_id     integer     NOT NULL REFERENCES dcp_setback_controls(id) ON DELETE CASCADE,
    r2_key         text        NOT NULL,
    council        text        NOT NULL,
    chapter_key    text        NOT NULL,
    version_label  text        NOT NULL,
    pdf_page       integer,
    verdict        text        NOT NULL CHECK (verdict IN ('verbatim', 'wrong_page', 'not_found', 'no_source')),
    quote_sha256   text        NOT NULL,
    checked_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (control_id, r2_key)
);

CREATE INDEX IF NOT EXISTS dcp_quote_version_check_council
    ON dcp_quote_version_check (council, chapter_key);

COMMENT ON TABLE dcp_quote_version_check IS
  'Per control and stored file version: is the control quote printed word for word on its cited page. Written only by scripts/dcp_quote_version_check.py. See migration 127.';

COMMIT;
