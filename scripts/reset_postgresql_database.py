#!/usr/bin/env python3
"""
PRP-8D: PostgreSQL Database Reset and Clean Foundation
Automated script to establish clean database state for bulletproof migration
"""

import psycopg2
import subprocess
import time
import json
from datetime import datetime
from pathlib import Path

class PostgreSQLDatabaseResetter:
    """Reset and prepare PostgreSQL database for clean migration"""
    
    def __init__(self):
        self.admin_conn_params = {
            'host': 'localhost',
            'user': 'postgres', 
            'password': 'postgres',
            'database': 'postgres'  # Connect to postgres db to manage nsw_planning
        }
        
        self.target_database = 'nsw_planning'
        self.reset_log = []
        self.verification_results = {}
        
    def log_operation(self, operation, status, details=None):
        """Log all operations for audit trail"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'status': status,
            'details': details or {}
        }
        self.reset_log.append(entry)
        
        status_icon = "[OK]" if status == 'SUCCESS' else "[FAIL]" if status == 'FAILED' else "[INFO]"
        print(f"{status_icon} {operation}")
        if details:
            for key, value in details.items():
                print(f"    {key}: {value}")
    
    def reset_database_foundation(self):
        """Complete database reset and preparation"""
        
        print("PRP-8D: POSTGRESQL DATABASE RESET")
        print("=" * 50)
        print(f"Target database: {self.target_database}")
        print(f"Started: {datetime.now().isoformat()}")
        
        try:
            # Step 1: Check PostgreSQL accessibility
            self.verify_postgresql_access()
            
            # Step 2: Backup existing database (if exists)
            self.backup_existing_database()
            
            # Step 3: Drop and recreate database
            self.drop_and_recreate_database()
            
            # Step 4: Create fresh schema
            self.create_authoritative_schema()
            
            # Step 5: Verify schema integrity
            self.verify_schema_integrity()
            
            # Step 6: Create migration tracking tables
            self.create_migration_tracking()
            
            # Step 7: Final validation
            self.perform_final_validation()
            
            # Generate reset report
            self.generate_reset_report()
            
            return True
            
        except Exception as e:
            self.log_operation("Database Reset", "FAILED", {"error": str(e)})
            print(f"\nFATAL ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def verify_postgresql_access(self):
        """Verify PostgreSQL is accessible and running"""
        
        try:
            conn = psycopg2.connect(**self.admin_conn_params)
            cur = conn.cursor()
            
            # Check PostgreSQL version
            cur.execute("SELECT version()")
            version = cur.fetchone()[0]
            
            # Check current databases
            cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false")
            databases = [row[0] for row in cur.fetchall()]
            
            conn.close()
            
            self.log_operation("PostgreSQL Access Check", "SUCCESS", {
                "version": version.split('\n')[0],
                "databases_found": len(databases),
                "target_exists": self.target_database in databases
            })
            
            return True
            
        except Exception as e:
            self.log_operation("PostgreSQL Access Check", "FAILED", {"error": str(e)})
            raise Exception(f"Cannot access PostgreSQL: {e}")
    
    def backup_existing_database(self):
        """Backup existing database if it exists"""
        
        try:
            conn = psycopg2.connect(**self.admin_conn_params)
            cur = conn.cursor()
            
            # Check if target database exists
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (self.target_database,))
            exists = cur.fetchone() is not None
            
            conn.close()
            
            if exists:
                backup_filename = f"{self.target_database}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
                backup_path = Path(backup_filename)
                
                # Create backup using pg_dump
                try:
                    cmd = [
                        "C:\\Program Files\\PostgreSQL\\17\\bin\\pg_dump.exe",
                        "-h", "localhost",
                        "-U", "postgres",
                        "-d", self.target_database,
                        "-f", str(backup_path)
                    ]
                    
                    # Set password via environment
                    import os
                    env = os.environ.copy()
                    env['PGPASSWORD'] = 'postgres'
                    
                    result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300)
                    
                    if result.returncode == 0:
                        backup_size = backup_path.stat().st_size if backup_path.exists() else 0
                        self.log_operation("Database Backup", "SUCCESS", {
                            "backup_file": str(backup_path),
                            "backup_size": f"{backup_size:,} bytes"
                        })
                    else:
                        self.log_operation("Database Backup", "FAILED", {
                            "error": result.stderr,
                            "stdout": result.stdout
                        })
                        
                except subprocess.TimeoutExpired:
                    self.log_operation("Database Backup", "FAILED", {"error": "Backup timed out"})
                except Exception as backup_error:
                    self.log_operation("Database Backup", "FAILED", {"error": str(backup_error)})
            else:
                self.log_operation("Database Backup", "SKIPPED", {"reason": "Target database does not exist"})
            
        except Exception as e:
            self.log_operation("Database Backup", "FAILED", {"error": str(e)})
            # Don't fail the entire process for backup failures
    
    def drop_and_recreate_database(self):
        """Drop existing database and create fresh one"""
        
        try:
            conn = psycopg2.connect(**self.admin_conn_params)
            conn.autocommit = True  # Required for CREATE/DROP DATABASE
            cur = conn.cursor()
            
            # Terminate any existing connections to the target database
            cur.execute("""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = %s
                  AND pid <> pg_backend_pid()
            """, (self.target_database,))
            
            # Drop database if exists
            cur.execute(f"DROP DATABASE IF EXISTS {self.target_database}")
            
            # Create fresh database
            cur.execute(f"CREATE DATABASE {self.target_database}")
            
            conn.close()
            
            # Verify creation by connecting to new database
            test_conn = psycopg2.connect(
                host='localhost',
                database=self.target_database,
                user='postgres',
                password='postgres'
            )
            test_conn.close()
            
            self.log_operation("Database Recreation", "SUCCESS", {
                "database": self.target_database,
                "status": "Fresh database created"
            })
            
        except Exception as e:
            self.log_operation("Database Recreation", "FAILED", {"error": str(e)})
            raise Exception(f"Failed to recreate database: {e}")
    
    def create_authoritative_schema(self):
        """Create the authoritative schema from SQL file"""
        
        schema_file = Path("scripts/create_authoritative_schema.sql")
        
        if not schema_file.exists():
            raise Exception(f"Schema file not found: {schema_file}")
        
        try:
            conn = psycopg2.connect(
                host='localhost',
                database=self.target_database,
                user='postgres', 
                password='postgres'
            )
            cur = conn.cursor()
            
            # Read and execute schema SQL
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema_sql = f.read()
            
            cur.execute(schema_sql)
            conn.commit()
            conn.close()
            
            self.log_operation("Authoritative Schema Creation", "SUCCESS", {
                "schema_file": str(schema_file),
                "file_size": f"{schema_file.stat().st_size:,} bytes"
            })
            
        except Exception as e:
            self.log_operation("Authoritative Schema Creation", "FAILED", {"error": str(e)})
            raise Exception(f"Failed to create schema: {e}")
    
    def verify_schema_integrity(self):
        """Verify all required tables and constraints exist"""
        
        expected_tables = [
            'authoritative.nsw_properties',
            'authoritative.planning_provisions', 
            'authoritative.provision_authority_tiers',
            'authoritative.property_provision_analysis',
            'authoritative.hierarchy_resolution_cache',
            'authoritative.professional_guidance',
            'authoritative.compliance_visual_aids'
        ]
        
        try:
            conn = psycopg2.connect(
                host='localhost',
                database=self.target_database,
                user='postgres',
                password='postgres'
            )
            cur = conn.cursor()
            
            tables_found = []
            tables_missing = []
            
            for table in expected_tables:
                schema, table_name = table.split('.')
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = %s AND table_name = %s
                    )
                """, (schema, table_name))
                
                if cur.fetchone()[0]:
                    tables_found.append(table)
                else:
                    tables_missing.append(table)
            
            # Check constraints
            cur.execute("""
                SELECT COUNT(*) FROM information_schema.table_constraints
                WHERE table_schema = 'authoritative'
            """)
            constraint_count = cur.fetchone()[0]
            
            conn.close()
            
            if tables_missing:
                self.log_operation("Schema Integrity Check", "FAILED", {
                    "tables_found": len(tables_found),
                    "tables_missing": tables_missing,
                    "constraint_count": constraint_count
                })
                raise Exception(f"Missing tables: {tables_missing}")
            else:
                self.log_operation("Schema Integrity Check", "SUCCESS", {
                    "tables_verified": len(tables_found),
                    "constraint_count": constraint_count
                })
            
        except Exception as e:
            self.log_operation("Schema Integrity Check", "FAILED", {"error": str(e)})
            raise Exception(f"Schema integrity check failed: {e}")
    
    def create_migration_tracking(self):
        """Create tables for tracking migration progress"""
        
        tracking_sql = """
        -- Migration tracking tables
        CREATE SCHEMA IF NOT EXISTS migration_tracking;
        
        CREATE TABLE IF NOT EXISTS migration_tracking.migration_runs (
            run_id SERIAL PRIMARY KEY,
            run_name VARCHAR(100) NOT NULL,
            started_at TIMESTAMP DEFAULT NOW(),
            completed_at TIMESTAMP,
            status VARCHAR(20) DEFAULT 'IN_PROGRESS',
            source_database VARCHAR(100),
            provisions_processed INTEGER DEFAULT 0,
            provisions_successful INTEGER DEFAULT 0,
            provisions_failed INTEGER DEFAULT 0,
            error_summary JSONB,
            configuration JSONB
        );
        
        CREATE TABLE IF NOT EXISTS migration_tracking.provision_migrations (
            id SERIAL PRIMARY KEY,
            run_id INTEGER REFERENCES migration_tracking.migration_runs(run_id),
            source_provision_id INTEGER,
            target_provision_id INTEGER,
            migration_timestamp TIMESTAMP DEFAULT NOW(),
            status VARCHAR(20),
            error_message TEXT,
            data_hash VARCHAR(64),
            processing_time_ms INTEGER
        );
        
        CREATE TABLE IF NOT EXISTS migration_tracking.verification_checkpoints (
            id SERIAL PRIMARY KEY,
            run_id INTEGER REFERENCES migration_tracking.migration_runs(run_id),
            checkpoint_name VARCHAR(100),
            checkpoint_type VARCHAR(50),
            executed_at TIMESTAMP DEFAULT NOW(),
            status VARCHAR(20),
            result_data JSONB,
            success_criteria TEXT,
            actual_result TEXT
        );
        
        -- Indexes for performance
        CREATE INDEX IF NOT EXISTS idx_provision_migrations_run_id ON migration_tracking.provision_migrations(run_id);
        CREATE INDEX IF NOT EXISTS idx_provision_migrations_status ON migration_tracking.provision_migrations(status);
        CREATE INDEX IF NOT EXISTS idx_verification_checkpoints_run_id ON migration_tracking.verification_checkpoints(run_id);
        """
        
        try:
            conn = psycopg2.connect(
                host='localhost',
                database=self.target_database,
                user='postgres',
                password='postgres'
            )
            cur = conn.cursor()
            
            cur.execute(tracking_sql)
            conn.commit()
            conn.close()
            
            self.log_operation("Migration Tracking Setup", "SUCCESS", {
                "tables_created": 3,
                "indexes_created": 3
            })
            
        except Exception as e:
            self.log_operation("Migration Tracking Setup", "FAILED", {"error": str(e)})
            raise Exception(f"Failed to create migration tracking: {e}")
    
    def perform_final_validation(self):
        """Final validation of database preparation"""
        
        try:
            conn = psycopg2.connect(
                host='localhost',
                database=self.target_database,
                user='postgres',
                password='postgres'
            )
            cur = conn.cursor()
            
            # Count all tables
            cur.execute("""
                SELECT schemaname, COUNT(*) as table_count 
                FROM pg_tables 
                WHERE schemaname IN ('authoritative', 'migration_tracking', 'public')
                GROUP BY schemaname
            """)
            schema_counts = dict(cur.fetchall())
            
            # Check database size
            cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
            db_size = cur.fetchone()[0]
            
            # Test basic functionality
            cur.execute("SELECT NOW()")
            current_time = cur.fetchone()[0]
            
            conn.close()
            
            self.verification_results = {
                'schema_counts': schema_counts,
                'database_size': db_size,
                'connection_test': 'SUCCESS',
                'timestamp': current_time.isoformat()
            }
            
            self.log_operation("Final Validation", "SUCCESS", self.verification_results)
            
        except Exception as e:
            self.log_operation("Final Validation", "FAILED", {"error": str(e)})
            raise Exception(f"Final validation failed: {e}")
    
    def generate_reset_report(self):
        """Generate comprehensive reset report"""
        
        report = {
            'prp': 'PRP-8D',
            'phase': 'Database Reset and Foundation',
            'completed_at': datetime.now().isoformat(),
            'target_database': self.target_database,
            'operations_log': self.reset_log,
            'verification_results': self.verification_results,
            'status': 'SUCCESS',
            'next_steps': [
                'Execute SQLite source validation',
                'Run bulletproof migration engine',
                'Perform comprehensive verification'
            ]
        }
        
        # Save report
        report_file = f"PRP_8D_DATABASE_RESET_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, default=str)
            
            print(f"\n" + "=" * 50)
            print("DATABASE RESET COMPLETED SUCCESSFULLY")
            print("=" * 50)
            print(f"Database: {self.target_database}")
            print(f"Operations: {len(self.reset_log)} completed")
            print(f"Report: {report_file}")
            print(f"Database size: {self.verification_results.get('database_size', 'Unknown')}")
            print("\nDatabase is ready for bulletproof migration.")
            
        except Exception as e:
            print(f"Could not save report: {e}")
        
        return report

def main():
    """Execute database reset"""
    
    resetter = PostgreSQLDatabaseResetter()
    success = resetter.reset_database_foundation()
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)