-- 063: per-LGA DCP plan "as at" date provenance (output-grounding campaign item 3).
--
-- One row per dcp_setback_controls.lga slug. Two independent evidence classes,
-- each stored with the date, its precision, and the verbatim evidence it was
-- read from — a date never appears without its basis:
--   portal_*  — NSW Planning Portal /dcp plan record (official planName/planURL;
--               the URL/name sometimes carries "as amended <date>")
--   stated_*  — the plan document's own commencement/amendment statement
--               (pages 1-10 of the local PDFs in data/dcps/)
-- The third basis, observed_current, is NOT stored here: it is read live from
-- dcp_chapter_registry.url_last_checked at serve time so it can never go stale
-- in a second place.
--
-- Precision honesty: precision records what the source actually states
-- ('day'/'month'/'year'). A month-precision date is stored as the 1st of the
-- month but must render as "March 2026", never "1 March 2026".

CREATE TABLE IF NOT EXISTS dcp_plan_as_at (
    lga                     text PRIMARY KEY,

    -- Planning Portal /dcp plan record (authority order 1)
    portal_prop_id          bigint,
    portal_lga_name         text,
    portal_plan_name        text,
    portal_plan_url         text,
    portal_date             date,
    portal_date_precision   text
        CHECK (portal_date_precision IN ('day', 'month', 'year')),
    portal_date_kind        text
        CHECK (portal_date_kind IN ('amended', 'effective', 'commenced', 'adopted')),
    portal_date_evidence    text,
    portal_checked_at       timestamptz,
    portal_raw              jsonb,

    -- The document's own statement (authority order 2)
    stated_date             date,
    stated_date_precision   text
        CHECK (stated_date_precision IN ('day', 'month', 'year')),
    stated_date_kind        text
        CHECK (stated_date_kind IN ('amended', 'effective', 'commenced', 'adopted')),
    stated_evidence         text,

    created_at              timestamptz NOT NULL DEFAULT now(),
    updated_at              timestamptz NOT NULL DEFAULT now(),

    -- A date never travels without its precision, kind and evidence.
    CHECK ((portal_date IS NULL) = (portal_date_precision IS NULL)),
    CHECK ((portal_date IS NULL) = (portal_date_kind IS NULL)),
    CHECK (portal_date IS NULL OR portal_date_evidence IS NOT NULL),
    CHECK ((stated_date IS NULL) = (stated_date_precision IS NULL)),
    CHECK ((stated_date IS NULL) = (stated_date_kind IS NULL)),
    CHECK (stated_date IS NULL OR stated_evidence IS NOT NULL)
);

COMMENT ON TABLE dcp_plan_as_at IS
  'Per-LGA DCP plan date provenance for served "as at" lines. Populated by '
  'scripts/fetch_dcp_as_at_dates.py (portal_*) and '
  'scripts/extract_dcp_stated_dates.py (stated_*). A row with both dates NULL '
  'means the LGA was checked and no dated evidence exists — serve-time falls '
  'back to dcp_chapter_registry.url_last_checked (observed_current) or renders '
  'no date line at all.';

-- dcp_setback_controls: basis column for the existing effective_date.
-- Existing values were parsed from dcp_version labels (migration 040) — that
-- has no defensible basis, so every pre-existing row stays NULL ("no recorded
-- basis") and the serve path never renders a per-row effective_date without a
-- basis. Future writers must set the basis alongside the date.
ALTER TABLE dcp_setback_controls
    ADD COLUMN IF NOT EXISTS effective_date_basis text
        CHECK (effective_date_basis IN
               ('stated_in_document', 'portal_url', 'observed_current'));

COMMENT ON COLUMN dcp_setback_controls.effective_date IS
  'Date the source DCP version took effect. Rows written before 2026-08 were '
  'parsed from dcp_version labels and carry effective_date_basis NULL — treat '
  'those as unattributed (do not render). Only a date with a non-NULL '
  'effective_date_basis is renderable.';

COMMENT ON COLUMN dcp_setback_controls.effective_date_basis IS
  'Provenance of effective_date: stated_in_document (the plan says so), '
  'portal_url (NSW Planning Portal plan record), observed_current (registry '
  'observation only). NULL = no recorded basis (legacy label-derived).';
