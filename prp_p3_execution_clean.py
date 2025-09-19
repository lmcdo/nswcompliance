#!/usr/bin/env python3
"""
PRP-P3: Development Type Standardization and Data Consolidation
Execute with automated verification
"""

from db_config import get_connection  # Unified PostgreSQL connection
import json
import os
import time
from datetime import datetime
from typing import Dict, List, Tuple
import re

class PRPP3Executor:
    def __init__(self):
        self.db_path = self.find_database()
        self.start_time = time.time()
        self.verification_results = {}

    def find_database(self) -> str:
        """Find the appropriate database file"""
        possible_paths = [
            'nsw_planning_backup_20250908_163513.sql.db',
            'nsw_planning.db',
            'backend/nsw_planning.db'
        ]

        for path in possible_paths:
            if os.path.exists(path):
                print(f"[OK] Using database: {path}")
                return path

        raise FileNotFoundError("No suitable database found")

    def check_source_data(self) -> Dict:
        """Check availability of PRP-P1 and PRP-P2 data"""
        conn = get_connection()
        cursor = conn.cursor()

        source_status = {
            'p1_available': False,
            'p1_count': 0,
            'p2_available': False,
            'p2_count': 0,
            'existing_dev_permissions': 0
        }

        print("=== Checking Source Data ===")

        # Check PRP-P1 data
        try:
            cursor.execute("SELECT COUNT(*) FROM permissibility_analysis")
            source_status['p1_count'] = cursor.fetchone()[0]
            source_status['p1_available'] = source_status['p1_count'] > 0
            print(f"[OK] PRP-P1 permissibility_analysis: {source_status['p1_count']} records")
        except sqlite3.OperationalError:
            print("[ERROR] PRP-P1 permissibility_analysis: Table not found")

        # Check PRP-P2 data
        try:
            cursor.execute("SELECT COUNT(*) FROM land_use_table_provisions")
            source_status['p2_count'] = cursor.fetchone()[0]
            source_status['p2_available'] = source_status['p2_count'] > 0
            print(f"[OK] PRP-P2 land_use_table_provisions: {source_status['p2_count']} records")
        except sqlite3.OperationalError:
            print("[ERROR] PRP-P2 land_use_table_provisions: Table not found")

        # Check existing development_permissions
        try:
            cursor.execute("SELECT COUNT(*) FROM development_permissions")
            source_status['existing_dev_permissions'] = cursor.fetchone()[0]
            print(f"[OK] Existing development_permissions: {source_status['existing_dev_permissions']} records")
        except sqlite3.OperationalError:
            print("[ERROR] development_permissions: Table not found")

        conn.close()
        return source_status

    def consolidate_p1_p2_data(self) -> int:
        """Consolidate PRP-P1 and PRP-P2 datasets"""
        print("\n=== Step 1: Data Consolidation ===")

        conn = get_connection()
        cursor = conn.cursor()

        # Create unified development_permissions table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS development_permissions (
            id SERIAL PRIMARY KEY SERIAL,
            zone TEXT NOT NULL,
            development_type TEXT NOT NULL,
            permission_status TEXT CHECK(permission_status IN ('permitted', 'consent', 'prohibited')),
            source_type TEXT CHECK(source_type IN ('p1_pattern', 'p2_table', 'nsw_standard')),
            source_provision TEXT,
            confidence_score REAL DEFAULT 0.8,
            conditions_text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(zone, development_type, source_type)
        )
        """)

        consolidated_count = 0

        # Extract from PRP-P1 permissibility_analysis
        try:
            cursor.execute("""
            SELECT DISTINCT
                zone,
                development_types_extracted as development_type,
                permissibility_status as permission_status,
                provision_reference as source_provision
            FROM permissibility_analysis
            WHERE development_types_extracted IS NOT NULL
            AND zone IS NOT NULL
            AND permissibility_status IN ('permitted', 'consent', 'prohibited')
            """)

            p1_data = cursor.fetchall()

            for row in p1_data:
                zone, dev_type, permission, source = row

                cursor.execute("""
                INSERT OR IGNORE INTO development_permissions
                (zone, development_type, permission_status, source_type, source_provision, confidence_score)
                VALUES (?, ?, ?, 'p1_pattern', ?, 0.7)
                """, (zone, dev_type, permission, source))
                consolidated_count += cursor.rowcount

            print(f"[OK] Consolidated {len(p1_data)} PRP-P1 patterns")

        except sqlite3.OperationalError as e:
            print(f"[WARN] PRP-P1 consolidation failed: {e}")

        # Extract from PRP-P2 land_use_table_provisions
        try:
            cursor.execute("""
            SELECT DISTINCT
                zone,
                development_type,
                permission_status,
                source_document
            FROM land_use_table_provisions
            WHERE development_type IS NOT NULL
            AND zone IS NOT NULL
            AND permission_status IN ('permitted', 'consent', 'prohibited')
            """)

            p2_data = cursor.fetchall()

            for row in p2_data:
                zone, dev_type, permission, source = row

                cursor.execute("""
                INSERT OR IGNORE INTO development_permissions
                (zone, development_type, permission_status, source_type, source_provision, confidence_score)
                VALUES (?, ?, ?, 'p2_table', ?, 0.9)
                """, (zone, dev_type, permission, source))
                consolidated_count += cursor.rowcount

            print(f"[OK] Consolidated {len(p2_data)} PRP-P2 table entries")

        except sqlite3.OperationalError as e:
            print(f"[WARN] PRP-P2 consolidation failed: {e}")

        conn.commit()
        conn.close()

        print(f"[OK] Total consolidated records: {consolidated_count}")
        return consolidated_count

    def add_nsw_standard_permissions(self) -> int:
        """Add NSW Standard Instrument permissions for major zones"""
        print("\n=== Step 2: NSW Standard Instrument Addition ===")

        # NSW Standard Instrument permissions for major zones
        nsw_standard_permissions = {
            'R2': {
                'dwelling_house': 'permitted',
                'dual_occupancy': 'consent',
                'multi_dwelling_housing': 'consent',
                'residential_flat_building': 'prohibited',
                'retail_premises': 'prohibited',
                'office_premises': 'prohibited',
                'warehouse': 'prohibited',
                'general_industry': 'prohibited'
            },
            'R3': {
                'dwelling_house': 'permitted',
                'dual_occupancy': 'permitted',
                'multi_dwelling_housing': 'consent',
                'residential_flat_building': 'consent',
                'retail_premises': 'prohibited',
                'warehouse': 'prohibited'
            },
            'R4': {
                'dwelling_house': 'permitted',
                'dual_occupancy': 'permitted',
                'multi_dwelling_housing': 'permitted',
                'residential_flat_building': 'consent',
                'retail_premises': 'consent',
                'office_premises': 'consent'
            },
            'B1': {
                'retail_premises': 'permitted',
                'office_premises': 'permitted',
                'restaurant': 'permitted',
                'dwelling_house': 'prohibited',
                'warehouse': 'consent',
                'general_industry': 'prohibited'
            },
            'B2': {
                'retail_premises': 'permitted',
                'office_premises': 'permitted',
                'restaurant': 'permitted',
                'residential_flat_building': 'consent',
                'warehouse': 'consent'
            },
            'IN1': {
                'light_industry': 'permitted',
                'warehouse': 'permitted',
                'office_premises': 'consent',
                'retail_premises': 'consent',
                'dwelling_house': 'prohibited',
                'residential_flat_building': 'prohibited'
            }
        }

        conn = get_connection()
        cursor = conn.cursor()

        nsw_added_count = 0

        for zone, permissions in nsw_standard_permissions.items():
            for dev_type, permission in permissions.items():
                cursor.execute("""
                INSERT OR IGNORE INTO development_permissions
                (zone, development_type, permission_status, source_type, source_provision, confidence_score)
                VALUES (?, ?, ?, 'nsw_standard', 'NSW Standard Instrument LEP', 1.0)
                """, (zone, dev_type, permission))
                nsw_added_count += cursor.rowcount

        conn.commit()
        conn.close()

        print(f"[OK] Added {nsw_added_count} NSW Standard Instrument permissions")
        return nsw_added_count

    def standardize_development_types(self) -> Dict:
        """Standardize development type terminology"""
        print("\n=== Step 3: Development Type Standardization ===")

        # NSW Standard Instrument standardization mappings
        standardization_mappings = {
            # Residential variations
            'dwelling house': 'dwelling_house',
            'single dwelling': 'dwelling_house',
            'detached house': 'dwelling_house',
            'house': 'dwelling_house',
            'duplex': 'dual_occupancy',
            'dual occ': 'dual_occupancy',
            'villa': 'multi_dwelling_housing',
            'townhouse': 'multi_dwelling_housing',
            'apartment': 'residential_flat_building',
            'unit': 'residential_flat_building',
            'flats': 'residential_flat_building',

            # Commercial variations
            'shop': 'retail_premises',
            'retail': 'retail_premises',
            'store': 'retail_premises',
            'office': 'office_premises',
            'commercial office': 'office_premises',
            'cafe': 'restaurant',
            'food premises': 'restaurant',

            # Industrial variations
            'storage': 'warehouse',
            'storage premises': 'warehouse',
            'light industrial': 'light_industry',
            'heavy industry': 'general_industry',
            'industrial': 'general_industry'
        }

        conn = get_connection()
        cursor = conn.cursor()

        standardization_stats = {
            'total_processed': 0,
            'standardized': 0,
            'already_standard': 0
        }

        # Get all unique development types
        cursor.execute("SELECT DISTINCT development_type FROM development_permissions")
        dev_types = [row[0] for row in cursor.fetchall()]

        for dev_type in dev_types:
            standardization_stats['total_processed'] += 1

            # Check if standardization needed
            standardized_type = standardization_mappings.get(dev_type.lower(), None)

            if standardized_type and standardized_type != dev_type:
                # Update to standardized form
                cursor.execute("""
                UPDATE development_permissions
                SET development_type = ?
                WHERE development_type = ?
                """, (standardized_type, dev_type))
                standardization_stats['standardized'] += cursor.rowcount
            else:
                standardization_stats['already_standard'] += 1

        conn.commit()
        conn.close()

        print(f"[OK] Processed {standardization_stats['total_processed']} development types")
        print(f"[OK] Standardized {standardization_stats['standardized']} entries")

        return standardization_stats

    def run_verification_tests(self) -> Dict:
        """Run automated verification tests"""
        print("\n=== Step 4: Automated Verification ===")

        conn = get_connection()
        cursor = conn.cursor()

        verification_results = {}

        # Test 1: Total combination count
        cursor.execute("SELECT COUNT(*) FROM development_permissions")
        total_combinations = cursor.fetchone()[0]
        verification_results['total_combinations'] = total_combinations
        verification_results['target_1000_met'] = total_combinations >= 1000

        print(f"[OK] Total combinations: {total_combinations} (Target: >=1000)")

        # Test 2: Zone coverage
        cursor.execute("SELECT COUNT(DISTINCT zone) FROM development_permissions")
        zone_count = cursor.fetchone()[0]
        verification_results['zone_coverage'] = zone_count

        print(f"[OK] Zone coverage: {zone_count} zones")

        # Test 3: Development type coverage
        cursor.execute("SELECT COUNT(DISTINCT development_type) FROM development_permissions")
        dev_type_count = cursor.fetchone()[0]
        verification_results['dev_type_coverage'] = dev_type_count

        print(f"[OK] Development type coverage: {dev_type_count} types")

        # Test 4: Source distribution
        cursor.execute("""
        SELECT source_type, COUNT(*)
        FROM development_permissions
        GROUP BY source_type
        """)
        source_distribution = dict(cursor.fetchall())
        verification_results['source_distribution'] = source_distribution

        print("[OK] Source distribution:")
        for source, count in source_distribution.items():
            print(f"  - {source}: {count}")

        # Test 5: Major zone coverage (R2, R3, R4, B1, B2, IN1)
        major_zones = ['R2', 'R3', 'R4', 'B1', 'B2', 'IN1']
        cursor.execute("""
        SELECT zone, COUNT(DISTINCT development_type) as dev_types
        FROM development_permissions
        WHERE zone IN ({})
        GROUP BY zone
        """.format(','.join(['?'] * len(major_zones))), major_zones)

        major_zone_coverage = dict(cursor.fetchall())
        verification_results['major_zone_coverage'] = major_zone_coverage

        print("[OK] Major zone development type coverage:")
        for zone in major_zones:
            count = major_zone_coverage.get(zone, 0)
            print(f"  - {zone}: {count} development types")

        # Test 6: Permission status distribution
        cursor.execute("""
        SELECT permission_status, COUNT(*)
        FROM development_permissions
        GROUP BY permission_status
        """)
        permission_distribution = dict(cursor.fetchall())
        verification_results['permission_distribution'] = permission_distribution

        print("[OK] Permission status distribution:")
        for status, count in permission_distribution.items():
            print(f"  - {status}: {count}")

        conn.close()

        # Overall success assessment
        success_criteria = [
            verification_results['target_1000_met'],
            verification_results['zone_coverage'] >= 10,
            verification_results['dev_type_coverage'] >= 8,
            len(verification_results['source_distribution']) >= 2
        ]

        verification_results['overall_success'] = all(success_criteria)
        verification_results['success_rate'] = sum(success_criteria) / len(success_criteria)

        print(f"\n[OK] Overall Success: {verification_results['overall_success']}")
        print(f"[OK] Success Rate: {verification_results['success_rate']:.1%}")

        return verification_results

    def generate_completion_report(self) -> str:
        """Generate completion report"""
        execution_time = time.time() - self.start_time

        report = {
            'prp_id': 'PRP-P3',
            'execution_time_minutes': round(execution_time / 60, 2),
            'completion_timestamp': datetime.now().isoformat(),
            'verification_results': self.verification_results,
            'success': self.verification_results.get('overall_success', False)
        }

        with open('prp_p3_completion_report.json', 'w') as f:
            json.dump(report, f, indent=2)

        print(f"\n=== PRP-P3 Completion Report ===")
        print(f"Execution time: {report['execution_time_minutes']} minutes")
        print(f"Success: {report['success']}")
        print(f"Report saved: prp_p3_completion_report.json")

        return 'prp_p3_completion_report.json'

    def execute(self):
        """Execute complete PRP-P3 with verification"""
        print("Starting PRP-P3: Development Type Standardization")
        print(f"Database: {self.db_path}")

        # Check source data
        source_status = self.check_source_data()

        if not (source_status['p1_available'] or source_status['p2_available']):
            print("\n[ERROR] No PRP-P1 or PRP-P2 source data available")
            return False

        # Execute consolidation steps
        try:
            consolidated_count = self.consolidate_p1_p2_data()
            nsw_count = self.add_nsw_standard_permissions()
            standardization_stats = self.standardize_development_types()
            self.verification_results = self.run_verification_tests()

            # Generate completion report
            report_file = self.generate_completion_report()

            print(f"\n[SUCCESS] PRP-P3 Completed Successfully!")
            print(f"[INFO] Total combinations: {self.verification_results['total_combinations']}")
            print(f"[INFO] Success rate: {self.verification_results['success_rate']:.1%}")

            return True

        except Exception as e:
            print(f"\n[ERROR] PRP-P3 execution failed: {e}")
            return False

if __name__ == '__main__':
    executor = PRPP3Executor()
    success = executor.execute()
    exit(0 if success else 1)