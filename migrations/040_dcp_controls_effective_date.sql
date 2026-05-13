-- Add effective_date to dcp_setback_controls
-- Queryable date for when the source DCP version took effect.
-- Enables: "was this control in effect on date X?"

ALTER TABLE dcp_setback_controls
ADD COLUMN IF NOT EXISTS effective_date date;

COMMENT ON COLUMN dcp_setback_controls.effective_date IS
  'Date the source DCP version took effect. Parsed from dcp_version where possible.';
