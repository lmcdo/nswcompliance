-- Migration: property-alerts delivery columns on threat_radar_subscriptions
-- Purpose: enable scheduled email dispatch + compliant unsubscribe for the
--          existing threat_radar subscription/check machinery.
-- Affected rows: 2 existing active subscriptions (backfilled below).
-- Spam Act 2003 note: consent = the explicit subscribe action; existing rows
--   are back-dated to their created_at as the consent timestamp.
-- STOP-and-ask: present to the user; run only after explicit approval + backup.

BEGIN;

-- 1. Tokenised unsubscribe link target (enumeration-safe; no email in the URL).
ALTER TABLE threat_radar_subscriptions
    ADD COLUMN IF NOT EXISTS unsubscribe_token TEXT;

-- Backfill tokens for existing rows before adding the UNIQUE + NOT NULL constraints.
UPDATE threat_radar_subscriptions
    SET unsubscribe_token = replace(gen_random_uuid()::text, '-', '')
    WHERE unsubscribe_token IS NULL;

ALTER TABLE threat_radar_subscriptions
    ALTER COLUMN unsubscribe_token SET NOT NULL;

-- Default new rows to a generated token (subscribe path need not set it explicitly).
ALTER TABLE threat_radar_subscriptions
    ALTER COLUMN unsubscribe_token SET DEFAULT replace(gen_random_uuid()::text, '-', '');

CREATE UNIQUE INDEX IF NOT EXISTS threat_radar_subscriptions_unsub_token_key
    ON threat_radar_subscriptions (unsubscribe_token);

-- 2. Consent timestamp (Spam Act record). Existing rows: their subscribe time.
ALTER TABLE threat_radar_subscriptions
    ADD COLUMN IF NOT EXISTS consented_at TIMESTAMPTZ;

UPDATE threat_radar_subscriptions
    SET consented_at = COALESCE(created_at, NOW())
    WHERE consented_at IS NULL;

ALTER TABLE threat_radar_subscriptions
    ALTER COLUMN consented_at SET DEFAULT NOW();

-- 3. Last successful notification send (advances only after a confirmed 2xx).
ALTER TABLE threat_radar_subscriptions
    ADD COLUMN IF NOT EXISTS last_notified_at TIMESTAMPTZ;

COMMIT;

-- Verify:
--   SELECT id, active, unsubscribe_token IS NOT NULL AS has_token,
--          consented_at, last_notified_at
--   FROM threat_radar_subscriptions;
