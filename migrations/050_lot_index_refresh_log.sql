-- Migration 050: lot_index_refresh_log
-- Per-LGA, per-phase record of when lot_search_index data was last refreshed.
-- Enables a factual "data as of" label in Prospector and event-driven refresh tracking.
-- See ~/.claude/plans/ce-lot-index-freshness-plan.md (item 1).

CREATE TABLE IF NOT EXISTS lot_index_refresh_log (
    id          BIGSERIAL PRIMARY KEY,
    lga_name    TEXT NOT NULL,
    phase       TEXT NOT NULL CHECK (phase IN ('overlays', 'fsr-assign', 'compute')),
    trigger     TEXT NOT NULL,          -- 'statewide_build' | 'monitor:<id>' | 'manual'
    started_at  TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    lots        INTEGER,
    status      TEXT NOT NULL DEFAULT 'running'   -- running | ok | failed
);

CREATE INDEX IF NOT EXISTS idx_lirl_lga ON lot_index_refresh_log (lga_name, finished_at DESC);

-- Backfill: one statewide_build row per LGA already present in the index, so the
-- "data as of" label has a baseline. Uses the index's own computed_at as the timestamp.
INSERT INTO lot_index_refresh_log (lga_name, phase, trigger, started_at, finished_at, lots, status)
SELECT lga_name, 'compute', 'statewide_build',
       MIN(computed_at), MAX(computed_at), COUNT(*), 'ok'
FROM lot_search_index
WHERE lga_name IS NOT NULL AND computed_at IS NOT NULL
GROUP BY lga_name;
