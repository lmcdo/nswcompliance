#!/usr/bin/env python3
"""
Simple PRP-V1 execution script
Creates the database version foundation
"""

import os
import sys
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from db_config import get_connection

def execute_prp_v1_sql(dry_run=True):
    """Execute PRP-V1 database schema creation"""

    print("PRP-V1: Database Foundation")
    print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
    print("=" * 50)

    # Create SQL script from PRP-V1 documentation
    sql_script = """
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
"""

    # Save SQL to file for reference
    sql_file = "prp_v1_schema.sql"
    with open(sql_file, "w") as f:
        f.write(sql_script)
    print(f"SQL script saved to: {sql_file}")

    if dry_run:
        print("DRY RUN: SQL script created but not executed")
        print("To execute: python execute_prp_v1.py --execute")
        return True

    # Execute SQL
    try:
        conn = get_connection()
        with conn.cursor() as cursor:
            print("Executing SQL script...")
            cursor.execute(sql_script)
            conn.commit()
        conn.close()
        print("SQL execution completed successfully")
        return True
    except Exception as e:
        print(f"SQL execution failed: {e}")
        return False

def run_verification():
    """Run PRP-V1 verification"""
    print("\nRunning PRP-V1 verification...")
    try:
        import subprocess
        result = subprocess.run([sys.executable, "verify_v1_database.py"],
                              capture_output=True, text=True)

        if result.returncode == 0:
            print("VERIFICATION PASSED")
            print(result.stdout)
            return True
        else:
            print("VERIFICATION FAILED")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"Verification error: {e}")
        return False

def main():
    """Main execution"""
    import argparse

    parser = argparse.ArgumentParser(description='Execute PRP-V1: Database Foundation')
    parser.add_argument('--execute', action='store_true',
                       help='Execute changes (default is dry run)')

    args = parser.parse_args()

    # Execute PRP-V1
    success = execute_prp_v1_sql(dry_run=not args.execute)

    if success:
        # Run verification
        verify_success = run_verification()

        if verify_success:
            print("\nPRP-V1 COMPLETED SUCCESSFULLY")
            return 0
        else:
            print("\nPRP-V1 VERIFICATION FAILED")
            return 1
    else:
        print("\nPRP-V1 EXECUTION FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())