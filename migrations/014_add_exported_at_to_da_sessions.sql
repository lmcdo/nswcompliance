-- Migration 014: Add exported_at column to da_sessions
-- Purpose: Track when a session's SEE PDF was last exported.
-- Used to show an informational banner when the planner edits a session after export.
-- Only the most recent export is tracked (not full history).

ALTER TABLE da_sessions ADD COLUMN IF NOT EXISTS exported_at TIMESTAMPTZ;
