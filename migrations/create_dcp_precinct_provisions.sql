-- Precinct Provisions Architecture - Table Creation
-- Date: 2025-10-23
-- Branch: feature/precinct-requirements-architecture

-- Core precinct provisions table
CREATE TABLE IF NOT EXISTS dcp_precinct_provisions (
    id SERIAL PRIMARY KEY,
    precinct_id TEXT NOT NULL,                    -- '9_29'
    precinct_name TEXT NOT NULL,                  -- 'South Western Marrickville'
    lga TEXT NOT NULL,                            -- 'Inner West' or 'Marrickville'
    provision_text TEXT NOT NULL,
    provision_type TEXT,                          -- 'objective', 'control', 'guideline'
    ref_number TEXT,                              -- '9.29.1', '9.29.2'
    section_header TEXT,                          -- 'Desired future character'
    parent_provision_id INTEGER REFERENCES regulatory_provisions(id),
    pdf_page INTEGER,
    display_order INTEGER DEFAULT 999,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_precinct_prov_lookup
    ON dcp_precinct_provisions(lga, precinct_id);

CREATE INDEX IF NOT EXISTS idx_precinct_prov_parent
    ON dcp_precinct_provisions(parent_provision_id);

CREATE INDEX IF NOT EXISTS idx_precinct_prov_type
    ON dcp_precinct_provisions(provision_type);

-- Precinct metadata table (optional, for future enhancements)
CREATE TABLE IF NOT EXISTS dcp_precinct_metadata (
    id SERIAL PRIMARY KEY,
    precinct_id TEXT NOT NULL UNIQUE,             -- '9_29'
    precinct_name TEXT NOT NULL,                  -- 'South Western Marrickville'
    lga TEXT NOT NULL,
    description TEXT,                             -- 'Established residential area...'
    desired_character TEXT,                       -- Extract from Part 9 introduction
    boundary_streets TEXT[],                      -- ['Illawarra Road', 'Hill Street', ...]
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_precinct_meta_lookup
    ON dcp_precinct_metadata(lga, precinct_id);

-- Verification query
DO $$
DECLARE
    table_count INTEGER;
    index_count INTEGER;
BEGIN
    -- Check tables created
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN ('dcp_precinct_provisions', 'dcp_precinct_metadata');

    -- Check indexes created
    SELECT COUNT(*) INTO index_count
    FROM pg_indexes
    WHERE tablename IN ('dcp_precinct_provisions', 'dcp_precinct_metadata');

    RAISE NOTICE 'Tables created: %', table_count;
    RAISE NOTICE 'Indexes created: %', index_count;

    IF table_count < 2 THEN
        RAISE EXCEPTION 'Table creation failed';
    END IF;

    RAISE NOTICE 'SUCCESS: Tables and indexes created';
END $$;
