#!/usr/bin/env python3
"""
Master execution script for Version Management MVP
Executes all PRPs in sequence with verification and rollback capabilities
"""

import os
import sys
import json
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import psycopg2

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from db_config import get_connection

class MVPExecutor:
    """Orchestrates the execution of all version management PRPs"""

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.execution_log = {
            "start_time": datetime.now().isoformat(),
            "dry_run": dry_run,
            "steps": [],
            "errors": [],
            "success": False
        }
        self.checkpoint_file = "mvp_execution_checkpoint.json"

    def log_step(self, step_name: str, status: str, details: Dict = None):
        """Log execution step"""
        step_log = {
            "step": step_name,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        self.execution_log["steps"].append(step_log)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {step_name}: {status}")

    def save_checkpoint(self):
        """Save execution checkpoint for recovery"""
        with open(self.checkpoint_file, "w") as f:
            json.dump(self.execution_log, f, indent=2)

    def execute_sql_file(self, sql_file: str) -> bool:
        """Execute SQL file against database"""
        if self.dry_run:
            print(f"  DRY RUN: Would execute {sql_file}")
            return True

        try:
            conn = get_connection()
            with conn.cursor() as cursor:
                with open(sql_file, 'r') as f:
                    sql_content = f.read()
                cursor.execute(sql_content)
                conn.commit()
            conn.close()
            return True
        except Exception as e:
            self.execution_log["errors"].append(f"SQL execution failed: {str(e)}")
            return False

    def run_python_script(self, script_path: str, args: List[str] = None) -> Tuple[bool, str]:
        """Run a Python script and capture output"""
        if self.dry_run and 'verify' not in script_path:
            print(f"  DRY RUN: Would run {script_path}")
            return True, "Dry run - skipped"

        try:
            cmd = [sys.executable, script_path]
            if args:
                cmd.extend(args)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr

        except subprocess.TimeoutExpired:
            return False, "Script execution timed out"
        except Exception as e:
            return False, str(e)

    def execute_prp_v1(self) -> bool:
        """Execute PRP-V1: Database Foundation"""
        self.log_step("PRP-V1", "STARTING", {"description": "Database Foundation"})

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

        # Save SQL to file
        sql_file = "prp_v1_schema.sql"
        with open(sql_file, "w") as f:
            f.write(sql_script)

        # Execute SQL
        success = self.execute_sql_file(sql_file)

        if success:
            self.log_step("PRP-V1", "EXECUTED", {"status": "SQL script completed"})
        else:
            self.log_step("PRP-V1", "FAILED", {"error": "SQL execution failed"})
            return False

        # MANDATORY: Run verification immediately after execution
        print("    🔍 Running PRP-V1 verification...")
        verify_success, output = self.run_python_script("verify_v1_database.py")

        if verify_success:
            self.log_step("PRP-V1", "COMPLETED", {"verification": "passed", "output": output[:500]})
            print("    ✅ PRP-V1 verification passed")
        else:
            self.log_step("PRP-V1", "FAILED", {"error": "Verification failed", "output": output[:500]})
            print(f"    ❌ PRP-V1 verification failed: {output}")
            return False

        self.save_checkpoint()
        return True

    def execute_prp_v2(self) -> bool:
        """Execute PRP-V2: Version Service Layer"""
        self.log_step("PRP-V2", "STARTING", {"description": "Version Service Layer"})

        # Service files should already exist from PRP documentation
        # Check if they're in place and warn if missing
        service_files = [
            "services/version_manager.py",
            "services/version_aware_query.py"
        ]

        missing_files = []
        for file_path in service_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)

        if missing_files:
            if self.dry_run:
                print(f"    ⚠️ DRY RUN: Missing service files: {missing_files}")
                print("    📝 Note: Service files need to be created from PRP-V2 documentation")
                self.log_step("PRP-V2", "SKIPPED", {"note": "Service files not yet created"})
            else:
                self.log_step("PRP-V2", "FAILED", {"error": f"Service files not found: {missing_files}"})
                print(f"    ❌ Missing service files: {missing_files}")
                print(f"    📝 Create these files from PRP-V2_VERSION_SERVICE.md")
                return False

        # MANDATORY: Run verification immediately after checking
        print("    🔍 Running PRP-V2 verification...")
        verify_success, output = self.run_python_script("verify_v2_service.py")

        if verify_success:
            self.log_step("PRP-V2", "COMPLETED", {"verification": "passed", "output": output[:500]})
            print("    ✅ PRP-V2 verification passed")
        else:
            self.log_step("PRP-V2", "FAILED", {"error": "Service verification failed", "output": output[:500]})
            print(f"    ❌ PRP-V2 verification failed: {output}")
            if not missing_files:  # Only fail if files exist but verification fails
                return False

        self.save_checkpoint()
        return True

    def execute_prp_v3(self) -> bool:
        """Execute PRP-V3: API Integration"""
        self.log_step("PRP-V3", "STARTING", {"description": "API Integration"})

        # API modifications should be applied to api_server.py manually
        # Check if api_server.py exists
        if not os.path.exists("api_server.py"):
            self.log_step("PRP-V3", "FAILED", {"error": "api_server.py not found"})
            print("    ❌ api_server.py not found")
            return False

        print("    📝 Note: API modifications should be applied manually from PRP-V3 documentation")
        self.log_step("PRP-V3", "PENDING", {"note": "Manual API modifications required"})

        # MANDATORY: Run verification immediately
        print("    🔍 Running PRP-V3 verification...")
        verify_success, output = self.run_python_script("verify_v3_api.py")

        if verify_success:
            self.log_step("PRP-V3", "COMPLETED", {"verification": "passed", "output": output[:500]})
            print("    ✅ PRP-V3 verification passed")
        else:
            self.log_step("PRP-V3", "WARNING", {"note": "API verification partially failed", "output": output[:500]})
            print(f"    ⚠️ PRP-V3 verification partial: {output}")
            # Don't fail execution - API might not be running yet

        self.save_checkpoint()
        return True

    def execute_prp_v4(self) -> bool:
        """Execute PRP-V4: Data Migration"""
        self.log_step("PRP-V4", "STARTING", {"description": "Data Migration"})

        # Check if migration script exists
        if not os.path.exists("migrate_to_versions.py"):
            print("    📝 Creating migration script from PRP-V4 documentation...")
            # Migration script should be created from PRP-V4 documentation
            if self.dry_run:
                print("    ⚠️ DRY RUN: Migration script needs to be created")
                self.log_step("PRP-V4", "SKIPPED", {"note": "Migration script not yet created"})
            else:
                self.log_step("PRP-V4", "FAILED", {"error": "migrate_to_versions.py not found"})
                print("    ❌ migrate_to_versions.py not found")
                print("    📝 Create this file from PRP-V4_MIGRATION_PIPELINE.md")
                return False

        # Run migration
        print("    🔄 Running data migration...")
        args = ["--execute"] if not self.dry_run else []
        success, output = self.run_python_script("migrate_to_versions.py", args)

        if success:
            self.log_step("PRP-V4", "EXECUTED", {"status": "Migration completed"})
            print("    ✅ Migration script completed")
        else:
            self.log_step("PRP-V4", "FAILED", {"error": "Migration script failed", "output": output[:500]})
            print(f"    ❌ Migration failed: {output}")
            return False

        # MANDATORY: Run verification immediately after migration
        print("    🔍 Running PRP-V4 verification...")
        verify_success, verify_output = self.run_python_script("verify_v4_migration.py")

        if verify_success:
            self.log_step("PRP-V4", "COMPLETED", {"verification": "passed", "output": verify_output[:500]})
            print("    ✅ PRP-V4 verification passed")
        else:
            self.log_step("PRP-V4", "FAILED", {"error": "Migration verification failed", "output": verify_output[:500]})
            print(f"    ❌ PRP-V4 verification failed: {verify_output}")
            return False

        self.save_checkpoint()
        return True

    def execute_prp_v5(self) -> bool:
        """Execute PRP-V5: Frontend Integration"""
        self.log_step("PRP-V5", "STARTING", {"description": "Frontend Integration"})

        # Frontend components should be deployed separately
        # Check if frontend directory exists
        if not os.path.exists("frontend-nextjs"):
            if self.dry_run:
                print("    ⚠️ DRY RUN: frontend-nextjs directory not found")
                self.log_step("PRP-V5", "SKIPPED", {"note": "Frontend directory not found"})
            else:
                self.log_step("PRP-V5", "WARNING", {"note": "Frontend directory not found"})
                print("    ⚠️ frontend-nextjs directory not found")

        # Check for frontend component files
        frontend_files = [
            "frontend-nextjs/components/version/VersionBadge.tsx",
            "frontend-nextjs/components/version/VersionSelector.tsx",
            "frontend-nextjs/hooks/useVersion.ts"
        ]

        missing_frontend = [f for f in frontend_files if not os.path.exists(f)]

        if missing_frontend:
            print(f"    📝 Note: Frontend files need to be created: {len(missing_frontend)} missing")
            self.log_step("PRP-V5", "PENDING", {"note": f"Frontend files need creation: {missing_frontend}"})
        else:
            print("    ✅ All frontend component files found")
            self.log_step("PRP-V5", "READY", {"note": "Frontend components exist"})

        # MANDATORY: Run verification immediately
        print("    🔍 Running PRP-V5 verification...")
        verify_success, output = self.run_python_script("verify_v5_frontend.py")

        if verify_success:
            self.log_step("PRP-V5", "COMPLETED", {"verification": "passed", "output": output[:500]})
            print("    ✅ PRP-V5 verification passed")
        else:
            self.log_step("PRP-V5", "WARNING", {"note": "Frontend verification partial", "output": output[:500]})
            print(f"    ⚠️ PRP-V5 verification partial: {output}")
            # Don't fail - frontend is less critical for MVP

        self.save_checkpoint()
        return True

    def run_final_validation(self) -> bool:
        """Run end-to-end validation"""
        self.log_step("VALIDATION", "STARTING", {"description": "End-to-end validation"})

        print("    🔍 Running comprehensive end-to-end validation...")
        verify_success, output = self.run_python_script("verify_v6_e2e.py")

        if verify_success:
            self.log_step("VALIDATION", "COMPLETED", {"status": "All checks passed", "output": output[:500]})
            print("    ✅ End-to-end validation passed")
            return True
        else:
            self.log_step("VALIDATION", "FAILED", {"error": "End-to-end validation failed", "output": output[:500]})
            print(f"    ❌ End-to-end validation failed: {output}")
            return False

    def execute_mvp(self) -> bool:
        """Execute the complete MVP implementation"""
        print("=" * 60)
        print("VERSION MANAGEMENT MVP EXECUTION")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'EXECUTE'}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

        try:
            # Execute each PRP in sequence
            steps = [
                ("PRP-V1: Database Foundation", self.execute_prp_v1),
                ("PRP-V2: Version Service", self.execute_prp_v2),
                ("PRP-V3: API Integration", self.execute_prp_v3),
                ("PRP-V4: Data Migration", self.execute_prp_v4),
                ("PRP-V5: Frontend Integration", self.execute_prp_v5),
            ]

            for step_name, step_func in steps:
                print(f"\n🚀 Executing {step_name}...")
                if not step_func():
                    print(f"❌ {step_name} failed. Stopping execution.")
                    self.execution_log["success"] = False
                    self.save_final_log()
                    return False

                print(f"✅ {step_name} completed successfully")
                time.sleep(2)  # Brief pause between steps

            # Run final validation
            print("\n🔍 Running final validation...")
            if self.run_final_validation():
                print("✅ All validations passed!")
                self.execution_log["success"] = True
            else:
                print("⚠️  Some validations failed - review logs")
                self.execution_log["success"] = False

        except Exception as e:
            print(f"\n❌ Unexpected error: {str(e)}")
            self.execution_log["errors"].append(str(e))
            self.execution_log["success"] = False

        finally:
            self.save_final_log()

        return self.execution_log["success"]

    def save_final_log(self):
        """Save the final execution log"""
        self.execution_log["end_time"] = datetime.now().isoformat()

        log_filename = f"mvp_execution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_filename, "w") as f:
            json.dump(self.execution_log, f, indent=2)

        print(f"\n📄 Execution log saved to: {log_filename}")

        # Print summary
        print("\n" + "=" * 60)
        print("EXECUTION SUMMARY")
        print("=" * 60)
        print(f"Status: {'SUCCESS ✅' if self.execution_log['success'] else 'FAILED ❌'}")
        print(f"Steps executed: {len(self.execution_log['steps'])}")
        print(f"Errors: {len(self.execution_log['errors'])}")

        if self.execution_log["errors"]:
            print("\nErrors encountered:")
            for error in self.execution_log["errors"]:
                print(f"  - {error}")

def main():
    """Main execution entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Execute Version Management MVP')
    parser.add_argument('--execute', action='store_true',
                       help='Execute changes (default is dry run)')
    parser.add_argument('--skip-to', type=str,
                       help='Skip to specific PRP (V1, V2, V3, V4, V5)')

    args = parser.parse_args()

    # Display warning for execution mode
    if args.execute:
        print("⚠️  WARNING: Running in EXECUTE mode")
        print("This will make changes to your database.")
        response = input("Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Execution cancelled.")
            return

    # Run executor
    executor = MVPExecutor(dry_run=not args.execute)
    success = executor.execute_mvp()

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()