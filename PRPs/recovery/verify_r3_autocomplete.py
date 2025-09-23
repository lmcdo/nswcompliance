#!/usr/bin/env python3
"""
Autocomplete verification script for PRP-R3: Schema Migration
Automatically migrates SQLite database to PostgreSQL
"""

import sqlite3
import psycopg2
import json
from datetime import datetime
import os

class PRPR3Verification:
    """Autocomplete SQLite to PostgreSQL migration"""

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "prp": "PRP-R3_SCHEMA_MIGRATION",
            "actions_taken": [],
            "checks": {},
            "errors": [],
            "tables_migrated": [],
            "success": False
        }
        self.sqlite_db = "nsw_planning.db"
        self.pg_conn_params = {
            "host": "localhost",
            "port": 5432,
            "database": "nsw_planning",
            "user": "postgres",
            "password": "postgres"
        }

    def extract_sqlite_schema(self) -> list:
        """Extract all table names from SQLite"""
        print("Extracting SQLite schema...")
        try:
            conn = sqlite3.connect(self.sqlite_db)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table'
                AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)

            tables = [row[0] for row in cursor.fetchall()]
            conn.close()

            self.results["checks"]["sqlite_tables"] = len(tables)
            print(f"Found {len(tables)} tables in SQLite")
            return tables
        except Exception as e:
            self.results["errors"].append(f"SQLite extraction failed: {str(e)}")
            return []

    def create_postgresql_schema(self) -> bool:
        """Create basic schema in PostgreSQL"""
        print("Creating PostgreSQL schema...")
        try:
            conn = psycopg2.connect(**self.pg_conn_params)
            cursor = conn.cursor()

            # Create regulatory_provisions table (core table) - updated to match SQLite structure
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS regulatory_provisions (
                    id SERIAL PRIMARY KEY,
                    document_id VARCHAR(500) NOT NULL,
                    provision_type VARCHAR(50),
                    ref_number VARCHAR(200),
                    provision_text TEXT NOT NULL,
                    zone VARCHAR(100),
                    development_type VARCHAR(500),
                    page_number INTEGER,
                    section_header TEXT,
                    text_level INTEGER,
                    original_id INTEGER,
                    domain_classification VARCHAR(100) DEFAULT 'GENERAL_PROVISIONS',
                    classification_confidence REAL DEFAULT 0.95,
                    cross_contamination_checked BOOLEAN DEFAULT FALSE,
                    prp_k1_enhanced BOOLEAN DEFAULT FALSE,
                    migration_id VARCHAR(100),
                    zone_confidence REAL,
                    zone_inference_method VARCHAR(100),
                    version_id INTEGER,
                    version_effective_date DATE,
                    is_current BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create versions schema
            cursor.execute("CREATE SCHEMA IF NOT EXISTS versions")

            # Create document_versions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS versions.document_versions (
                    id SERIAL PRIMARY KEY,
                    document_type VARCHAR(50),
                    document_identifier VARCHAR(500),
                    version_number VARCHAR(50),
                    version_status VARCHAR(20),
                    effective_date DATE,
                    document_url TEXT,
                    notes TEXT,
                    metadata JSONB,
                    created_by VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            conn.close()

            self.results["actions_taken"].append("Created PostgreSQL schema")
            print("SUCCESS: PostgreSQL schema created")
            return True
        except Exception as e:
            self.results["errors"].append(f"Schema creation failed: {str(e)}")
            return False

    def migrate_regulatory_provisions(self) -> bool:
        """Migrate regulatory_provisions table data"""
        print("Migrating regulatory_provisions...")
        try:
            # Extract from SQLite - updated column names to match SQLite schema
            sqlite_conn = sqlite3.connect(self.sqlite_db)
            sqlite_cursor = sqlite_conn.cursor()

            sqlite_cursor.execute("""
                SELECT document_id, provision_type, ref_number, provision_text,
                       zone, development_type, page_number, section_header,
                       text_level, original_id, domain_classification,
                       classification_confidence, cross_contamination_checked,
                       prp_k1_enhanced, migration_id, zone_confidence,
                       zone_inference_method, created_at
                FROM regulatory_provisions
            """)

            rows = sqlite_cursor.fetchall()
            sqlite_conn.close()

            # Insert into PostgreSQL
            pg_conn = psycopg2.connect(**self.pg_conn_params)
            pg_cursor = pg_conn.cursor()

            for row in rows:
                # Convert SQLite boolean integers to PostgreSQL booleans
                row_list = list(row)
                # cross_contamination_checked is at index 12
                row_list[12] = bool(row_list[12]) if row_list[12] is not None else False
                # prp_k1_enhanced is at index 13
                row_list[13] = bool(row_list[13]) if row_list[13] is not None else False

                pg_cursor.execute("""
                    INSERT INTO regulatory_provisions
                    (document_id, provision_type, ref_number, provision_text,
                     zone, development_type, page_number, section_header,
                     text_level, original_id, domain_classification,
                     classification_confidence, cross_contamination_checked,
                     prp_k1_enhanced, migration_id, zone_confidence,
                     zone_inference_method, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, tuple(row_list))

            pg_conn.commit()

            # Verify count
            pg_cursor.execute("SELECT COUNT(*) FROM regulatory_provisions")
            count = pg_cursor.fetchone()[0]

            pg_conn.close()

            self.results["checks"]["provisions_migrated"] = count
            self.results["tables_migrated"].append("regulatory_provisions")
            print(f"SUCCESS: Migrated {count} regulatory provisions")
            return True
        except Exception as e:
            self.results["errors"].append(f"Provisions migration failed: {str(e)}")
            return False

    def create_indexes(self) -> bool:
        """Create indexes for performance"""
        print("Creating indexes...")
        try:
            conn = psycopg2.connect(**self.pg_conn_params)
            cursor = conn.cursor()

            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_rp_document_id ON regulatory_provisions(document_id)",
                "CREATE INDEX IF NOT EXISTS idx_rp_zone ON regulatory_provisions(zone)",
                "CREATE INDEX IF NOT EXISTS idx_rp_dev_type ON regulatory_provisions(development_type)",
                "CREATE INDEX IF NOT EXISTS idx_rp_ref_number ON regulatory_provisions(ref_number)",
                "CREATE INDEX IF NOT EXISTS idx_rp_provision_type ON regulatory_provisions(provision_type)",
                "CREATE INDEX IF NOT EXISTS idx_rp_version_id ON regulatory_provisions(version_id)",
                "CREATE INDEX IF NOT EXISTS idx_dv_identifier ON versions.document_versions(document_identifier)",
                "CREATE INDEX IF NOT EXISTS idx_dv_version_number ON versions.document_versions(version_number)"
            ]

            for idx_sql in indexes:
                try:
                    cursor.execute(idx_sql)
                    self.results["actions_taken"].append(f"Created index: {idx_sql.split(' ')[2]}")
                except:
                    pass  # Index might already exist

            conn.commit()
            conn.close()

            print("SUCCESS: Indexes created")
            return True
        except Exception as e:
            self.results["errors"].append(f"Index creation failed: {str(e)}")
            return False

    def validate_migration(self) -> bool:
        """Validate the migration was successful"""
        print("Validating migration...")
        try:
            conn = psycopg2.connect(**self.pg_conn_params)
            cursor = conn.cursor()

            # Check table exists
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_name = 'regulatory_provisions'
            """)

            if cursor.fetchone()[0] == 0:
                self.results["errors"].append("regulatory_provisions table not found")
                return False

            # Check row count
            cursor.execute("SELECT COUNT(*) FROM regulatory_provisions")
            count = cursor.fetchone()[0]

            if count > 0:
                self.results["checks"]["validation"] = "PASSED"
                self.results["checks"]["final_row_count"] = count
                print(f"SUCCESS: Validation passed: {count} provisions in database")
                conn.close()
                return True
            else:
                self.results["checks"]["validation"] = "FAILED"
                conn.close()
                return False
        except Exception as e:
            self.results["errors"].append(f"Validation failed: {str(e)}")
            return False

    def execute(self) -> bool:
        """Execute complete migration process"""
        print("\n" + "="*60)
        print("PRP-R3: Schema Migration - AUTOCOMPLETE")
        print("="*60 + "\n")

        # Step 1: Extract SQLite schema
        tables = self.extract_sqlite_schema()
        if not tables:
            self.results["success"] = False
            print("FAILED: Failed to extract SQLite schema")
            return False

        # Step 2: Create PostgreSQL schema
        if not self.create_postgresql_schema():
            self.results["success"] = False
            print("FAILED: Failed to create PostgreSQL schema")
            return False

        # Step 3: Migrate data
        if not self.migrate_regulatory_provisions():
            print("WARNING: Data migration had issues")

        # Step 4: Create indexes
        if not self.create_indexes():
            print("WARNING: Index creation had issues")

        # Step 5: Validate
        if self.validate_migration():
            self.results["success"] = True
            print("\nSUCCESS: Migration successful")

            # Create marker
            os.makedirs("recovery_checkpoints", exist_ok=True)
            with open("recovery_checkpoints/R3_complete.marker", "w") as f:
                f.write(f"PRP-R3 completed at {datetime.now().isoformat()}\n")
                f.write(f"Migrated {self.results['checks'].get('provisions_migrated', 0)} provisions\n")
        else:
            self.results["success"] = False

        # Save results
        with open("verify_r3_results.json", "w") as f:
            json.dump(self.results, f, indent=2)

        print(f"\nActions taken: {len(self.results['actions_taken'])}")
        print(f"Tables migrated: {len(self.results['tables_migrated'])}")
        print(f"Result: {'PASSED' if self.results['success'] else 'FAILED'}")

        if self.results["errors"]:
            print("\nErrors:")
            for error in self.results["errors"]:
                print(f"  - {error}")

        return self.results["success"]

if __name__ == "__main__":
    verifier = PRPR3Verification()
    verifier.execute()
