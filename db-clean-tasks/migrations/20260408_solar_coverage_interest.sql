-- Solar coverage interest signups
-- Captures demand for Geoscape building data by address/suburb
-- Used to prioritise NSW coverage expansion beyond Google Solar metro area

CREATE TABLE IF NOT EXISTS solar_coverage_interest (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT NOT NULL,
    address     TEXT NOT NULL,
    suburb      TEXT,
    postcode    TEXT,
    lat         DOUBLE PRECISION,
    lng         DOUBLE PRECISION,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- Prevent duplicate signups for the same email+address combination
CREATE UNIQUE INDEX IF NOT EXISTS solar_coverage_interest_email_address
    ON solar_coverage_interest (email, address);

-- Index for querying by suburb/postcode to identify high-demand areas
CREATE INDEX IF NOT EXISTS solar_coverage_interest_suburb
    ON solar_coverage_interest (suburb);

CREATE INDEX IF NOT EXISTS solar_coverage_interest_postcode
    ON solar_coverage_interest (postcode);
