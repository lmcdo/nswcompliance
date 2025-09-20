
-- PRP-V1: Database Version Foundation
CREATE SCHEMA IF NOT EXISTS versions;

-- Main version registry table
CREATE TABLE IF NOT EXISTS versions.document_versions (
    id SERIAL PRIMARY KEY,
    document_type VARCHAR(20) NOT NULL CHECK (document_type IN ('SEPP', 'LEP', 'DCP')),
    document_identifier VARCHAR(255) NOT NULL,
    version_number VARCHAR(20) NOT NULL,
    version_status VARCHAR(20) NOT NULL CHECK (version_status IN ('CURRENT', 'PREVIOUS', 'ARCHIVED')),
    effective_date DATE NOT NULL,
    superseded_date DATE,
    document_url TEXT,
    change_summary TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'system',
    UNIQUE(document_type, document_identifier, version_status)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_version_lookup ON versions.document_versions(document_type, document_identifier, version_status);
CREATE INDEX IF NOT EXISTS idx_version_dates ON versions.document_versions(effective_date, superseded_date);
CREATE INDEX IF NOT EXISTS idx_version_current ON versions.document_versions(version_status) WHERE version_status = 'CURRENT';

-- Add version columns to existing tables
ALTER TABLE regulatory_provisions
    ADD COLUMN IF NOT EXISTS version_id INTEGER REFERENCES versions.document_versions(id),
    ADD COLUMN IF NOT EXISTS is_current BOOLEAN DEFAULT true,
    ADD COLUMN IF NOT EXISTS version_effective_date DATE;

ALTER TABLE development_controls
    ADD COLUMN IF NOT EXISTS version_id INTEGER REFERENCES versions.document_versions(id),
    ADD COLUMN IF NOT EXISTS is_current BOOLEAN DEFAULT true;

ALTER TABLE quantitative_standards
    ADD COLUMN IF NOT EXISTS version_id INTEGER REFERENCES versions.document_versions(id),
    ADD COLUMN IF NOT EXISTS is_current BOOLEAN DEFAULT true;

-- Create audit table
CREATE TABLE IF NOT EXISTS versions.version_audit_log (
    id SERIAL PRIMARY KEY,
    version_id INTEGER REFERENCES versions.document_versions(id),
    action VARCHAR(50) NOT NULL,
    action_details JSONB,
    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    performed_by VARCHAR(100)
);

-- Create helper functions
CREATE OR REPLACE FUNCTION versions.get_current_version(
    p_doc_type VARCHAR,
    p_doc_identifier VARCHAR
) RETURNS INTEGER AS $$
DECLARE
    v_version_id INTEGER;
BEGIN
    SELECT id INTO v_version_id
    FROM versions.document_versions
    WHERE document_type = p_doc_type
      AND document_identifier = p_doc_identifier
      AND version_status = 'CURRENT'
    LIMIT 1;

    RETURN v_version_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION versions.get_version_at_date(
    p_doc_type VARCHAR,
    p_doc_identifier VARCHAR,
    p_date DATE
) RETURNS INTEGER AS $$
DECLARE
    v_version_id INTEGER;
BEGIN
    SELECT id INTO v_version_id
    FROM versions.document_versions
    WHERE document_type = p_doc_type
      AND document_identifier = p_doc_identifier
      AND effective_date <= p_date
      AND (superseded_date IS NULL OR superseded_date > p_date)
    ORDER BY effective_date DESC
    LIMIT 1;

    RETURN v_version_id;
END;
$$ LANGUAGE plpgsql;

-- Create audit trigger function
CREATE OR REPLACE FUNCTION versions.log_version_change()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO versions.version_audit_log(version_id, action, action_details, performed_by)
        VALUES (NEW.id, 'CREATE', row_to_json(NEW), COALESCE(NEW.created_by, 'system'));
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO versions.version_audit_log(version_id, action, action_details, performed_by)
        VALUES (NEW.id, 'UPDATE', jsonb_build_object('old', row_to_json(OLD), 'new', row_to_json(NEW)), 'system');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Attach trigger
DROP TRIGGER IF EXISTS version_audit_trigger ON versions.document_versions;
CREATE TRIGGER version_audit_trigger
AFTER INSERT OR UPDATE ON versions.document_versions
FOR EACH ROW EXECUTE FUNCTION versions.log_version_change();
