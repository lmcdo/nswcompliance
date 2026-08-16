-- DCP Interest / waitlist table
-- Run once in Supabase SQL editor to enable the register-interest flow.

CREATE TABLE IF NOT EXISTS dcp_interest (
  id          BIGSERIAL PRIMARY KEY,
  email       TEXT        NOT NULL,
  council_name TEXT       NOT NULL,
  address     TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (email, council_name)
);

-- Index for the demand dashboard query (GROUP BY council_name)
CREATE INDEX IF NOT EXISTS dcp_interest_council_idx ON dcp_interest (council_name);

-- Optional: view for quick demand summary
CREATE OR REPLACE VIEW dcp_interest_demand AS
  SELECT council_name, COUNT(*) AS interest_count
  FROM dcp_interest
  GROUP BY council_name
  ORDER BY interest_count DESC;
