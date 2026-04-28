-- Migration: forum_monitor_queue
-- Stores forum threads identified by the forum-monitor Trigger.dev task.
-- Status: pending → approved (user tapped ✓) or skipped (user tapped ✗)

CREATE TABLE IF NOT EXISTS forum_monitor_queue (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    forum       TEXT NOT NULL,          -- 'PropertyChat' | 'Whirlpool'
    section     TEXT NOT NULL,          -- e.g. 'Development', 'Finance & Strategy'
    thread_url  TEXT NOT NULL UNIQUE,   -- dedup key — same thread never alerted twice
    thread_title TEXT NOT NULL,
    thread_body  TEXT,
    draft_response TEXT NOT NULL,
    product     TEXT NOT NULL,          -- which of the 5 products matched
    status      TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'skipped')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_forum_monitor_queue_status ON forum_monitor_queue (status);
CREATE INDEX IF NOT EXISTS idx_forum_monitor_queue_created ON forum_monitor_queue (created_at DESC);
