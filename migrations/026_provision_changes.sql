-- Migration 026: Provision change log + spatial tracking
-- =========================================================
-- Adds:
--   provision_changes  — audit trail of every DCP provision change detected
--   is_spatial         — flag on dcp_chapter_registry for map/appendix PDFs
--                        that are hash-tracked but not extracted

-- ── provision_changes ────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS provision_changes (
    id                  SERIAL PRIMARY KEY,
    changed_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    council             TEXT NOT NULL,
    chapter_key         TEXT NOT NULL,
    dcp_version         TEXT NOT NULL,         -- version label at time of change (e.g. 'v1.2')
    ref_number          TEXT NOT NULL,
    change_type         TEXT NOT NULL,
    -- change_type values:
    --   'changed'              — provision text updated
    --   'added'                — new provision inserted
    --   'removed'              — provision soft-deleted
    --   'renumbered'           — ref_number changed, text largely same
    --   'page_shift'           — pdf_page offset changed, text unchanged
    --   'map_change'           — spatial/map document changed (no text diff possible)
    --   'regeneration_artifact'— PDF re-exported with no substantive content change
    --   'restructure'          — >50% provisions unmatched; full replace used
    old_text            TEXT,
    new_text            TEXT,
    old_ref_number      TEXT,                  -- populated for 'renumbered' entries
    has_numeric_change  BOOLEAN DEFAULT FALSE, -- TRUE if numeric values differ between old/new
    old_pdf_page        INT,
    new_pdf_page        INT,
    reviewed_at         TIMESTAMPTZ,           -- NULL = change not yet reviewed
    notes               TEXT                   -- optional human reviewer annotation
);

CREATE INDEX IF NOT EXISTS provision_changes_council_chapter_idx
    ON provision_changes (council, chapter_key, changed_at DESC);

CREATE INDEX IF NOT EXISTS provision_changes_changed_at_idx
    ON provision_changes (changed_at DESC);

CREATE INDEX IF NOT EXISTS provision_changes_type_idx
    ON provision_changes (change_type);

CREATE INDEX IF NOT EXISTS provision_changes_numeric_idx
    ON provision_changes (has_numeric_change)
    WHERE has_numeric_change = TRUE;

-- ── is_spatial column on dcp_chapter_registry ────────────────────────────────

ALTER TABLE dcp_chapter_registry
    ADD COLUMN IF NOT EXISTS is_spatial BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN dcp_chapter_registry.is_spatial IS
    'TRUE for map/diagram/appendix PDFs that are hash-tracked for changes '
    'but not extracted as text provisions. When their hash changes, a '
    'map_change alert is sent for manual review.';
