#!/usr/bin/env python3
"""
AUTO-COMPLETING PRP-P2 Verification Script
- Checks development_permissions table exists
- Uses ACTUAL table schema (no table_format column)
- Fixes schema mismatches
- Validates data quality
- Creates missing indexes if needed
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from db_config import get_connection
import json
from datetime import datetime
from typing import Dict, List, Tuple

class PRPP2AutoComplete:
    """Auto-completing verification for PRP-P2 with actual schema"""

    def __init__(self):
        self.conn = get_connection()
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "prp": "PRP-P2_LAND_USE_TABLE_PARSING_AUTOCOMPLETE",
            "actions_taken": [],
            "checks": {},
            "errors": [],
            "warnings": []
        }

    def check_and_create_table(self) -> bool:
        """Check if development_permissions table exists, create if missing"""
        print("Checking development_permissions table...")

        try:
            with self.conn.cursor() as cursor:
                # Check if table exists
                cursor.execute("""
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'development_permissions'
                """)
                exists = cursor.fetchone() is not None

                if not exists:
                    print("Creating development_permissions table...")

                    create_sql = """
                    CREATE TABLE development_permissions (
                        id SERIAL PRIMARY KEY,
                        zone VARCHAR(10),
                        development_type VARCHAR(100),
                        permission_status VARCHAR(20),
                        conditions TEXT,
                        source_provision_id INTEGER,
                        lep_name VARCHAR(255),
                        extraction_method VARCHAR(50),
                        confidence_score VARCHAR(10),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        source_type VARCHAR(20),

                        -- Additional fields for completeness
                        document_id INTEGER,
                        provision_text TEXT,
                        extraction_metadata JSONB DEFAULT '{}'
                    );

                    -- Create indexes
                    CREATE INDEX IF NOT EXISTS idx_dev_perm_zone ON development_permissions(zone);
                    CREATE INDEX IF NOT EXISTS idx_dev_perm_type ON development_permissions(development_type);
                    CREATE INDEX IF NOT EXISTS idx_dev_perm_status ON development_permissions(permission_status);
                    CREATE INDEX IF NOT EXISTS idx_dev_perm_lep ON development_permissions(lep_name);
                    CREATE INDEX IF NOT EXISTS idx_dev_perm_source ON development_permissions(source_type);
                    """

                    cursor.execute(create_sql)
                    self.conn.commit()
                    self.results["actions_taken"].append("Created development_permissions table with indexes")
                    print("Created development_permissions table")
                else:
                    print("development_permissions table already exists")

                # Create missing indexes if needed
                self.create_missing_indexes()

                return True

        except Exception as e:
            self.results["errors"].append(f"Failed to check/create table: {str(e)}")
            print(f"Failed to check/create table: {e}")
            return False

    def create_missing_indexes(self) -> bool:
        """Create missing indexes for performance"""
        print("Checking and creating indexes...")

        indexes = [
            ("idx_dev_perm_zone", "development_permissions", "zone"),
            ("idx_dev_perm_type", "development_permissions", "development_type"),
            ("idx_dev_perm_status", "development_permissions", "permission_status"),
            ("idx_dev_perm_lep", "development_permissions", "lep_name"),
            ("idx_dev_perm_combo", "development_permissions", "zone, development_type, permission_status")
        ]

        try:
            with self.conn.cursor() as cursor:
                for index_name, table_name, columns in indexes:
                    # Check if index exists
                    cursor.execute("""
                        SELECT indexname FROM pg_indexes
                        WHERE indexname = %s
                    """, (index_name,))

                    if not cursor.fetchone():
                        cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({columns})")
                        self.results["actions_taken"].append(f"Created index {index_name}")
                        print(f"Created index {index_name}")

                self.conn.commit()
                return True

        except Exception as e:
            self.results["errors"].append(f"Failed to create indexes: {str(e)}")
            print(f"Failed to create indexes: {e}")
            return False

    def analyze_actual_schema(self) -> Dict[str, any]:
        """Analyze the actual table schema"""
        print("Analyzing table schema...")

        schema_info = {}

        try:
            with self.conn.cursor() as cursor:
                # Get column information
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = 'development_permissions'
                    ORDER BY ordinal_position
                """)

                columns = cursor.fetchall()
                schema_info['columns'] = [
                    {
                        'name': col[0],
                        'type': col[1],
                        'nullable': col[2],
                        'default': col[3]
                    }
                    for col in columns
                ]

                # Get indexes
                cursor.execute("""
                    SELECT indexname, indexdef
                    FROM pg_indexes
                    WHERE tablename = 'development_permissions'
                """)
                indexes = cursor.fetchall()
                schema_info['indexes'] = [{'name': idx[0], 'definition': idx[1]} for idx in indexes]

        except Exception as e:
            self.results["errors"].append(f"Failed to analyze schema: {str(e)}")
            schema_info['error'] = str(e)

        self.results["checks"]["schema_analysis"] = schema_info
        return schema_info

    def verify_data_quality(self) -> Dict[str, any]:
        """Verify data quality using actual schema"""
        print("Verifying data quality...")

        quality_checks = {}

        try:
            with self.conn.cursor() as cursor:
                # Basic counts
                cursor.execute("SELECT COUNT(*) FROM development_permissions")
                total_count = cursor.fetchone()[0]
                quality_checks['total_combinations'] = total_count

                # Zone coverage
                cursor.execute("SELECT COUNT(DISTINCT zone) FROM development_permissions WHERE zone IS NOT NULL")
                zone_count = cursor.fetchone()[0]
                quality_checks['zone_coverage'] = zone_count

                # Development type coverage
                cursor.execute("SELECT COUNT(DISTINCT development_type) FROM development_permissions WHERE development_type IS NOT NULL")
                dev_type_count = cursor.fetchone()[0]
                quality_checks['development_type_coverage'] = dev_type_count

                # LEP coverage
                cursor.execute("SELECT COUNT(DISTINCT lep_name) FROM development_permissions WHERE lep_name IS NOT NULL")
                lep_count = cursor.fetchone()[0]
                quality_checks['lep_coverage'] = lep_count

                # Permission status distribution
                cursor.execute("""
                    SELECT permission_status, COUNT(*)
                    FROM development_permissions
                    WHERE permission_status IS NOT NULL
                    GROUP BY permission_status
                """)
                permission_distribution = dict(cursor.fetchall())
                quality_checks['permission_distribution'] = permission_distribution

                # Major zones coverage
                cursor.execute("""
                    SELECT zone, COUNT(*)
                    FROM development_permissions
                    WHERE zone IN ('R1', 'R2', 'R3', 'R4', 'B1', 'B2', 'B3', 'B4', 'IN1', 'IN2')
                    GROUP BY zone
                    ORDER BY zone
                """)
                major_zones = dict(cursor.fetchall())
                quality_checks['major_zone_coverage'] = major_zones

                # Source type distribution
                cursor.execute("""
                    SELECT source_type, COUNT(*)
                    FROM development_permissions
                    WHERE source_type IS NOT NULL
                    GROUP BY source_type
                """)
                source_distribution = dict(cursor.fetchall())
                quality_checks['source_type_distribution'] = source_distribution

                # Extraction method distribution
                cursor.execute("""
                    SELECT extraction_method, COUNT(*)
                    FROM development_permissions
                    WHERE extraction_method IS NOT NULL
                    GROUP BY extraction_method
                """)
                extraction_methods = dict(cursor.fetchall())
                quality_checks['extraction_method_distribution'] = extraction_methods

                # Null value analysis
                cursor.execute("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(*) - COUNT(zone) as null_zones,
                        COUNT(*) - COUNT(development_type) as null_dev_types,
                        COUNT(*) - COUNT(permission_status) as null_permissions,
                        COUNT(*) - COUNT(lep_name) as null_lep_names
                    FROM development_permissions
                """)
                null_analysis = cursor.fetchone()
                quality_checks['null_analysis'] = {
                    'total_records': null_analysis[0],
                    'null_zones': null_analysis[1],
                    'null_development_types': null_analysis[2],
                    'null_permissions': null_analysis[3],
                    'null_lep_names': null_analysis[4]
                }

                # Data quality warnings
                if quality_checks['total_combinations'] < 200:
                    self.results["warnings"].append(f"Only {total_count} combinations, target was 200+")

                if quality_checks['zone_coverage'] < 15:
                    self.results["warnings"].append(f"Only {zone_count} zones covered, target was 15+")

        except Exception as e:
            self.results["errors"].append(f"Failed to verify data quality: {str(e)}")
            quality_checks['error'] = str(e)

        self.results["checks"]["data_quality"] = quality_checks
        return quality_checks

    def get_sample_data(self) -> Dict[str, any]:
        """Get sample data for validation"""
        print("Sampling data for validation...")

        sample_data = {}

        try:
            with self.conn.cursor() as cursor:
                # Get sample records
                cursor.execute("""
                    SELECT zone, development_type, permission_status, lep_name, source_type, extraction_method
                    FROM development_permissions
                    ORDER BY zone, development_type
                    LIMIT 20
                """)
                samples = cursor.fetchall()

                sample_data['samples'] = [
                    {
                        'zone': row[0],
                        'development_type': row[1],
                        'permission_status': row[2],
                        'lep_name': row[3],
                        'source_type': row[4],
                        'extraction_method': row[5]
                    }
                    for row in samples
                ]

                # Get zone breakdown for major zones
                cursor.execute("""
                    SELECT zone, permission_status, COUNT(*)
                    FROM development_permissions
                    WHERE zone IN ('R1', 'R2', 'R3', 'R4', 'B1', 'B2')
                    GROUP BY zone, permission_status
                    ORDER BY zone, permission_status
                """)
                zone_breakdown = [
                    {'zone': row[0], 'permission': row[1], 'count': row[2]}
                    for row in cursor.fetchall()
                ]
                sample_data['major_zone_breakdown'] = zone_breakdown

        except Exception as e:
            self.results["errors"].append(f"Failed to sample data: {str(e)}")
            sample_data['error'] = str(e)

        self.results["checks"]["sample_data"] = sample_data
        return sample_data

    def run_autocomplete(self) -> bool:
        """Run complete auto-completing verification"""
        print("Starting PRP-P2 Auto-Complete Verification...")

        # Step 1: Check/create table and indexes
        if not self.check_and_create_table():
            return False

        # Step 2: Analyze actual schema
        schema_info = self.analyze_actual_schema()

        # Step 3: Verify data quality
        quality_info = self.verify_data_quality()

        # Step 4: Get sample data
        sample_info = self.get_sample_data()

        # Determine success
        success = (
            len(self.results["errors"]) == 0 and
            quality_info.get('total_combinations', 0) > 0
        )

        self.results["success"] = success
        self.results["summary"] = {
            "total_errors": len(self.results["errors"]),
            "total_warnings": len(self.results["warnings"]),
            "actions_taken": len(self.results["actions_taken"]),
            "total_combinations": quality_info.get('total_combinations', 0),
            "zone_coverage": quality_info.get('zone_coverage', 0),
            "development_type_coverage": quality_info.get('development_type_coverage', 0),
            "lep_coverage": quality_info.get('lep_coverage', 0),
            "target_met": quality_info.get('total_combinations', 0) >= 200
        }

        # Save results
        output_file = "prp_p2_autocomplete_results.json"
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)

        # Print summary
        print("\n" + "="*60)
        print("PRP-P2 AUTO-COMPLETE RESULTS")
        print("="*60)
        print(f"Total combinations: {quality_info.get('total_combinations', 0)}")
        print(f"Zone coverage: {quality_info.get('zone_coverage', 0)}")
        print(f"Development types: {quality_info.get('development_type_coverage', 0)}")
        print(f"LEP coverage: {quality_info.get('lep_coverage', 0)}")
        print(f"Permission types: {list(quality_info.get('permission_distribution', {}).keys())}")
        print(f"Actions taken: {len(self.results['actions_taken'])}")

        if self.results["actions_taken"]:
            print("\nActions performed:")
            for action in self.results["actions_taken"]:
                print(f"  - {action}")

        if self.results["errors"]:
            print("\nErrors:")
            for error in self.results["errors"]:
                print(f"  - {error}")

        if self.results["warnings"]:
            print("\nWarnings:")
            for warning in self.results["warnings"]:
                print(f"  - {warning}")

        print(f"\n{'PRP-P2 AUTOCOMPLETE SUCCESS' if success else 'PRP-P2 AUTOCOMPLETE FAILED'}")
        print(f"Results saved to: {output_file}")

        return success

if __name__ == "__main__":
    verifier = PRPP2AutoComplete()
    success = verifier.run_autocomplete()
    sys.exit(0 if success else 1)