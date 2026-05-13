-- Add last_verified_at to dcp_setback_controls
-- Updated by r2_monitor when the source chapter is confirmed unchanged.
-- Enables user-facing currency display: "Last verified: 2026-05-13"

ALTER TABLE dcp_setback_controls
ADD COLUMN IF NOT EXISTS last_verified_at timestamptz;

-- Backfill: set to created_at for existing rows (conservative — we know
-- the data was correct when extracted, but haven't verified since)
UPDATE dcp_setback_controls
SET last_verified_at = created_at
WHERE last_verified_at IS NULL;

COMMENT ON COLUMN dcp_setback_controls.last_verified_at IS
  'Last time the source chapter was confirmed unchanged by the DCP monitor';
