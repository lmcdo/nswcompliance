-- Create PRP-P1 required tables for permissibility pattern extraction

-- Main permissibility analysis table
CREATE TABLE IF NOT EXISTS permissibility_analysis (
    id SERIAL PRIMARY KEY,
    provision_id INTEGER,
    zone TEXT,
    pattern_type TEXT,
    extracted_text TEXT,
    development_types TEXT, -- JSON array
    permission_status TEXT, -- permitted/prohibited/consent
    confidence_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Additional fields for better tracking
    document_id TEXT,
    lep_name TEXT,
    provision_category TEXT,
    extraction_metadata JSONB DEFAULT '{}'
);

-- Pattern validation table for QA
CREATE TABLE IF NOT EXISTS pattern_validation (
    id SERIAL PRIMARY KEY,
    pattern_type TEXT,
    sample_text TEXT,
    expected_result TEXT,
    validation_status TEXT, -- pass/fail/manual_review
    validated_by TEXT,
    validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_permissibility_zone ON permissibility_analysis(zone);
CREATE INDEX IF NOT EXISTS idx_permissibility_permission ON permissibility_analysis(permission_status);
CREATE INDEX IF NOT EXISTS idx_permissibility_pattern ON permissibility_analysis(pattern_type);
CREATE INDEX IF NOT EXISTS idx_permissibility_dev_types ON permissibility_analysis USING gin(to_tsvector('english', development_types));

-- Foreign key constraint if provisions table exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'regulatory_provisions') THEN
        ALTER TABLE permissibility_analysis
        ADD CONSTRAINT fk_permissibility_provision
        FOREIGN KEY (provision_id) REFERENCES regulatory_provisions(id);
    END IF;
END $$;