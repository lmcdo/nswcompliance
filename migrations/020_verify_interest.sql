-- Verify app professional registration / email capture
-- Captures interest signals from the assessment page:
--   - council not yet processed (replaces dcp_interest for new captures)
--   - professional wanting to save/export assessments
--   - general interest in the product

CREATE TABLE IF NOT EXISTS verify_interest (
  id            BIGSERIAL PRIMARY KEY,
  email         TEXT NOT NULL,
  role          TEXT,              -- planner, certifier, architect, conveyancer, agent, other
  council_name  TEXT,              -- which council they were viewing (if any)
  address       TEXT,              -- which address they searched
  source        TEXT NOT NULL DEFAULT 'assessment',  -- assessment, dcp_notify, export
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- One registration per email+source combo to avoid duplicates
CREATE UNIQUE INDEX IF NOT EXISTS verify_interest_email_source_idx
  ON verify_interest (email, source);

-- Demand analysis: which councils drive the most interest
CREATE INDEX IF NOT EXISTS verify_interest_council_idx
  ON verify_interest (council_name) WHERE council_name IS NOT NULL;
