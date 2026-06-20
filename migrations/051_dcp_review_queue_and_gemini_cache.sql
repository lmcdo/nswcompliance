-- 051_dcp_review_queue_and_gemini_cache.sql
-- Foundation for the governed DCP review loop. See docs/DCP_PIPELINE_ARCHITECTURE_2026-06.md §5.
-- Two ADDITIVE tables. No changes to existing tables and nothing in live serving paths.
-- Not applied automatically — apply with a backup per Database Safety rules.

-- ── 1. Review queue ─────────────────────────────────────────────────────────
-- Every detected provision change a human must approve before it goes live.
-- Embeds the §5.1/§5.2 design: field-class gate (has_numeric_change), currency
-- (source_content_hash), atomic claim (status + claimed_by for SELECT ... FOR
-- UPDATE SKIP LOCKED), and the named-human audit trail (reviewed_by/reason).
CREATE TABLE IF NOT EXISTS dcp_review_queue (
    id                   BIGSERIAL PRIMARY KEY,
    council              TEXT        NOT NULL,
    chapter_key          TEXT        NOT NULL,
    document_id          TEXT,
    ref_number           TEXT,                       -- provision identifier within the chapter
    change_type          TEXT        NOT NULL,       -- changed | added | removed | restructure
    old_text             TEXT,
    new_text             TEXT,
    old_page             INTEGER,
    new_page             INTEGER,
    has_numeric_change   BOOLEAN     NOT NULL DEFAULT FALSE,  -- field-class gate: TRUE => always human
    numeric_diff         JSONB,                      -- {"old": [...], "new": [...]}
    source_content_hash  TEXT,                       -- currency: chapter hash this change came from
    crop_url             TEXT,                       -- PDF page crop for review (populated later)
    summary              TEXT,                       -- plain-language "what changed" (Gemini later)
    gemini_actionable    BOOLEAN,                    -- Stage-3 actionability verdict (later), nullable
    status               TEXT        NOT NULL DEFAULT 'pending',
    claimed_by           TEXT,                       -- worker/reviewer holding the row
    claimed_at           TIMESTAMPTZ,
    reviewed_by          TEXT,                       -- named human (audit trail)
    reviewed_at          TIMESTAMPTZ,
    review_reason        TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT dcp_review_queue_status_chk
        CHECK (status IN ('pending', 'in_progress', 'approved', 'rejected', 'needs_info')),
    CONSTRAINT dcp_review_queue_change_type_chk
        CHECK (change_type IN ('changed', 'added', 'removed', 'restructure'))
);

-- Worklist queries: pending items, worst/riskiest first (numeric changes), by council.
CREATE INDEX IF NOT EXISTS idx_dcp_review_queue_pending
    ON dcp_review_queue (has_numeric_change DESC, created_at)
    WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_dcp_review_queue_council_status
    ON dcp_review_queue (council, status);
CREATE INDEX IF NOT EXISTS idx_dcp_review_queue_chapter
    ON dcp_review_queue (chapter_key);

COMMENT ON TABLE dcp_review_queue IS
    'Human-review queue for detected DCP provision changes. Nothing commits to '
    'regulatory_provisions without an approved row here (governance gate).';

-- ── 2. Gemini classification cache ──────────────────────────────────────────
-- See §5.4. Keyed by content hash + model + prompt version so a re-pass over
-- unchanged provisions makes zero API calls, and identical text always yields
-- the identical verdict (kills Gemini non-determinism / verdict flapping).
CREATE TABLE IF NOT EXISTS gemini_classification_cache (
    text_sha256      TEXT        NOT NULL,
    model_name       TEXT        NOT NULL,
    prompt_version   TEXT        NOT NULL DEFAULT 'v1',
    is_actionable    BOOLEAN     NOT NULL,
    verified         BOOLEAN     NOT NULL,
    identified_text  TEXT,
    char_start       INTEGER,
    char_end         INTEGER,
    reason           TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (text_sha256, model_name, prompt_version)
);

COMMENT ON TABLE gemini_classification_cache IS
    'Durable cache for GeminiActionabilityClassifier verdicts. Bump prompt_version '
    'to invalidate after a prompt change.';
