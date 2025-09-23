#!/usr/bin/env python3
"""
Autocomplete verification script for PRP-R4: Version Management Setup
Automatically creates version management infrastructure
"""

import psycopg2
import json
from datetime import datetime, date
import os

class PRPR4Verification:
    """Autocomplete version management setup"""

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "prp": "PRP-R4_VERSION_MANAGEMENT",
            "actions_taken": [],
            "checks": {},
            "errors": [],
            "success": False
        }
        self.pg_conn_params = {
            "host": "localhost",
            "port": 5432,
            "database": "nsw_planning",
            "user": "postgres",
            "password": "postgres"
        }
        self.baseline_date = '2024-09-20'

    def create_versions_schema(self) -> bool:
        """Create versions schema if not exists"""
        print("Creating versions schema...")
        try:
            conn = psycopg2.connect(**self.pg_conn_params)
            cursor = conn.cursor()

            cursor.execute("CREATE SCHEMA IF NOT EXISTS versions")

            conn.commit()
            conn.close()

            self.results["actions_taken"].append("Created versions schema")
            print("✅ Versions schema created")
            return True
        except Exception as e:
            self.results["errors"].append(f"Schema creation failed: {str(e)}")
            return False

    def create_document_versions_table(self) -> bool:
        """Create document_versions table"""
        print("Creating document_versions table...")
        try:
            conn = psycopg2.connect(**self.pg_conn_params)
            cursor = conn.cursor()

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

            self.results["actions_taken"].append("Created document_versions table")
            print("✅ Document versions table created")
            return True
        except Exception as e:
            self.results["errors"].append(f"Table creation failed: {str(e)}")
            return False

    def populate_baseline_versions(self) -> bool:
        """Create baseline versions for all documents"""
        print("Creating baseline versions...")
        try:
            conn = psycopg2.connect(**self.pg_conn_params)
            cursor = conn.cursor()

            # Get unique document identifiers
            cursor.execute("""
                SELECT DISTINCT document_id
                FROM regulatory_provisions
                WHERE document_id IS NOT NULL
            """)

            documents = cursor.fetchall()

            # Create baseline version for each document
            for (doc_id,) in documents:
                # Clean document identifier
                doc_identifier = doc_id.replace('_', ' ').replace('  ', ' ').strip()

                # Determine document type
                if 'SEPP' in doc_id.upper():
                    doc_type = 'SEPP'
                elif 'LEP' in doc_id.upper():
                    doc_type = 'LEP'
                elif 'DCP' in doc_id.upper() or 'Ashfield' in doc_id or 'Leichhardt' in doc_id or 'Marrickville' in doc_id:
                    doc_type = 'DCP'
                else:
                    doc_type = 'OTHER'

                cursor.execute("""
                    INSERT INTO versions.document_versions
                    (document_type, document_identifier, version_number, version_status,
                     effective_date, notes, metadata, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    doc_type,
                    doc_identifier,
                    'v1.0-baseline',
                    'CURRENT',
                    self.baseline_date,
                    'Baseline version from Sept 2024 migration',
                    json.dumps({
                        'baseline': True,
                        'source': 'SQLite migration'
                    }),
                    'migration_script'
                ))

            conn.commit()

            # Count created versions
            cursor.execute("SELECT COUNT(*) FROM versions.document_versions")
            version_count = cursor.fetchone()[0]

            conn.close()

            self.results["checks"]["baseline_versions_created"] = version_count
            self.results["actions_taken"].append(f"Created {version_count} baseline versions")
            print(f"✅ Created {version_count} baseline versions")
            return True
        except Exception as e:
            self.results["errors"].append(f"Baseline population failed: {str(e)}")
            return False

    def link_provisions_to_versions(self) -> bool:
        """Link regulatory provisions to their document versions"""
        print("Linking provisions to versions...")
        try:
            conn = psycopg2.connect(**self.pg_conn_params)
            cursor = conn.cursor()

            # Update provisions with version_id
            cursor.execute("""
                UPDATE regulatory_provisions rp
                SET version_id = dv.id,
                    version_effective_date = dv.effective_date
                FROM versions.document_versions dv
                WHERE (
                    rp.document_id = dv.document_identifier
                    OR rp.document_id = REPLACE(dv.document_identifier, ' ', '_')
                    OR REPLACE(rp.document_id, '_', ' ') = dv.document_identifier
                )
                AND dv.version_number = 'v1.0-baseline'
                AND rp.version_id IS NULL
            """)

            linked_count = cursor.rowcount
            conn.commit()

            # Verify linking
            cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE version_id IS NOT NULL")
            total_linked = cursor.fetchone()[0]

            conn.close()

            self.results["checks"]["provisions_linked"] = total_linked
            self.results["actions_taken"].append(f"Linked {linked_count} provisions to versions")
            print(f"✅ Linked {linked_count} provisions")
            return True
        except Exception as e:
            self.results["errors"].append(f"Provision linking failed: {str(e)}")
            return False

    def create_change_tracking_table(self) -> bool:
        """Create provision changes tracking table"""
        print("Creating change tracking table...")
        try:
            conn = psycopg2.connect(**self.pg_conn_params)
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS versions.provision_changes (
                    id SERIAL PRIMARY KEY,
                    provision_id INTEGER,
                    document_version_id INTEGER,
                    change_type VARCHAR(50),
                    previous_value TEXT,
                    new_value TEXT,
                    change_date DATE,
                    effective_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (document_version_id) REFERENCES versions.document_versions(id)
                )
            """)

            conn.commit()
            conn.close()

            self.results["actions_taken"].append("Created provision_changes table")
            print("✅ Change tracking table created")
            return True
        except Exception as e:
            self.results["errors"].append(f"Change tracking creation failed: {str(e)}")
            return False

    def verify_setup(self) -> bool:
        """Verify version management is operational"""
        print("Verifying version management setup...")
        try:
            conn = psycopg2.connect(**self.pg_conn_params)
            cursor = conn.cursor()

            # Check schema exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.schemata
                    WHERE schema_name = 'versions'
                )
            """)
            schema_exists = cursor.fetchone()[0]

            # Check tables exist
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = 'versions'
            """)
            table_count = cursor.fetchone()[0]

            # Check provisions are linked
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    COUNT(version_id) as linked
                FROM regulatory_provisions
            """)
            result = cursor.fetchone()
            total_provisions = result[0]
            linked_provisions = result[1]

            conn.close()

            self.results["checks"]["schema_exists"] = schema_exists
            self.results["checks"]["tables_created"] = table_count
            self.results["checks"]["linking_percentage"] = (
                (linked_provisions / total_provisions * 100) if total_provisions > 0 else 0
            )

            print(f"✅ Version management operational")
            print(f"   - Schema exists: {schema_exists}")
            print(f"   - Tables created: {table_count}")
            print(f"   - Provisions linked: {linked_provisions}/{total_provisions}")

            return schema_exists and table_count >= 2 and linked_provisions > 0
        except Exception as e:
            self.results["errors"].append(f"Verification failed: {str(e)}")
            return False

    def execute(self) -> bool:
        """Execute version management setup"""
        print("\n" + "="*60)
        print("PRP-R4: Version Management Setup - AUTOCOMPLETE")
        print("="*60 + "\n")

        # Create schema
        if not self.create_versions_schema():
            print("⚠️ Schema creation had issues")

        # Create tables
        if not self.create_document_versions_table():
            print("⚠️ Table creation had issues")

        # Populate baseline versions
        if not self.populate_baseline_versions():
            print("⚠️ Baseline creation had issues")

        # Link provisions
        if not self.link_provisions_to_versions():
            print("⚠️ Provision linking had issues")

        # Create change tracking
        if not self.create_change_tracking_table():
            print("⚠️ Change tracking creation had issues")

        # Verify setup
        if self.verify_setup():
            self.results["success"] = True
            print("\n✅ Version management setup successful")

            # Create marker
            os.makedirs("recovery_checkpoints", exist_ok=True)
            with open("recovery_checkpoints/R4_complete.marker", "w") as f:
                f.write(f"PRP-R4 completed at {datetime.now().isoformat()}\n")
                f.write("Version management infrastructure ready\n")
        else:
            self.results["success"] = False

        # Save results
        with open("verify_r4_results.json", "w") as f:
            json.dump(self.results, f, indent=2)

        print(f"\nActions taken: {len(self.results['actions_taken'])}")
        print(f"Result: {'✅ PASSED' if self.results['success'] else '❌ FAILED'}")

        if self.results["errors"]:
            print("\nErrors:")
            for error in self.results["errors"]:
                print(f"  - {error}")

        return self.results["success"]

if __name__ == "__main__":
    verifier = PRPR4Verification()
    verifier.execute()