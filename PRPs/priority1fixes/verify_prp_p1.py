#!/usr/bin/env python3
"""
Verification script for PRP-P1: Phase 1 - Permissibility Pattern Extraction
Validates that permissibility analysis tables and data were created correctly
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from db_config import get_connection
import json
from datetime import datetime
from typing import Dict, List, Tuple

class PRPP1Verification:
    """Verify PRP-P1 implementation completeness"""

    def __init__(self):
        self.conn = get_connection()
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "prp": "PRP-P1_PERMISSIBILITY_EXTRACTION",
            "checks": {},
            "errors": [],
            "warnings": []
        }

    def check_tables_exist(self) -> Dict[str, bool]:
        """Check if required tables exist"""
        required_tables = [
            'permissibility_analysis',
            'pattern_validation'
        ]

        table_checks = {}
        with self.conn.cursor() as cursor:
            for table in required_tables:
                cursor.execute("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = %s
                """, (table,))

                exists = cursor.fetchone() is not None
                table_checks[table] = exists

                if not exists:
                    self.results["errors"].append(f"Table {table} not found")

        self.results["checks"]["tables"] = table_checks
        return table_checks

    def check_permissibility_data(self) -> Dict[str, any]:
        """Check permissibility_analysis table data quality"""
        data_checks = {}

        with self.conn.cursor() as cursor:
            try:
                # Check total extractions
                cursor.execute("SELECT COUNT(*) FROM permissibility_analysis")
                total_count = cursor.fetchone()[0]
                data_checks['total_extractions'] = total_count

                if total_count < 500:
                    self.results["warnings"].append(f"Only {total_count} extractions found, target was 500+")

                # Check zone coverage
                cursor.execute("SELECT COUNT(DISTINCT zone) FROM permissibility_analysis")
                zone_count = cursor.fetchone()[0]
                data_checks['zone_coverage'] = zone_count

                if zone_count < 15:
                    self.results["warnings"].append(f"Only {zone_count} zones covered, target was 15+")

                # Check permission types
                cursor.execute("""
                    SELECT permission_status, COUNT(*)
                    FROM permissibility_analysis
                    GROUP BY permission_status
                """)
                permission_types = dict(cursor.fetchall())
                data_checks['permission_types'] = permission_types

                expected_types = {'permitted', 'prohibited', 'consent'}
                found_types = set(permission_types.keys())
                if not expected_types.issubset(found_types):
                    missing = expected_types - found_types
                    self.results["errors"].append(f"Missing permission types: {missing}")

                # Check pattern types
                cursor.execute("""
                    SELECT pattern_type, COUNT(*)
                    FROM permissibility_analysis
                    GROUP BY pattern_type
                """)
                pattern_types = dict(cursor.fetchall())
                data_checks['pattern_types'] = pattern_types

                # Check development types diversity
                cursor.execute("""
                    SELECT COUNT(DISTINCT development_types)
                    FROM permissibility_analysis
                    WHERE development_types IS NOT NULL
                """)
                dev_type_diversity = cursor.fetchone()[0]
                data_checks['development_type_diversity'] = dev_type_diversity

                if dev_type_diversity < 8:
                    self.results["warnings"].append(f"Only {dev_type_diversity} unique development types, target was 8+")

            except Exception as e:
                self.results["errors"].append(f"Error checking permissibility data: {str(e)}")
                data_checks['error'] = str(e)

        self.results["checks"]["permissibility_data"] = data_checks
        return data_checks

    def check_data_quality(self) -> Dict[str, any]:
        """Check data quality metrics"""
        quality_checks = {}

        with self.conn.cursor() as cursor:
            try:
                # Check for null values in critical fields
                cursor.execute("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(*) - COUNT(zone) as null_zones,
                        COUNT(*) - COUNT(permission_status) as null_permissions,
                        COUNT(*) - COUNT(extracted_text) as null_text
                    FROM permissibility_analysis
                """)
                result = cursor.fetchone()
                quality_checks['null_analysis'] = {
                    'total_records': result[0],
                    'null_zones': result[1],
                    'null_permissions': result[2],
                    'null_extracted_text': result[3]
                }

                # Check for duplicates
                cursor.execute("""
                    SELECT COUNT(*) - COUNT(DISTINCT (zone, extracted_text, permission_status))
                    FROM permissibility_analysis
                """)
                duplicates = cursor.fetchone()[0]
                quality_checks['duplicate_count'] = duplicates

                if duplicates > 0:
                    self.results["warnings"].append(f"{duplicates} potential duplicate extractions found")

                # Check confidence scores if available
                cursor.execute("""
                    SELECT AVG(confidence_score), MIN(confidence_score), MAX(confidence_score)
                    FROM permissibility_analysis
                    WHERE confidence_score IS NOT NULL
                """)
                confidence_result = cursor.fetchone()
                if confidence_result[0] is not None:
                    quality_checks['confidence_scores'] = {
                        'average': float(confidence_result[0]),
                        'minimum': float(confidence_result[1]),
                        'maximum': float(confidence_result[2])
                    }

            except Exception as e:
                self.results["errors"].append(f"Error checking data quality: {str(e)}")
                quality_checks['error'] = str(e)

        self.results["checks"]["data_quality"] = quality_checks
        return quality_checks

    def check_sample_extractions(self) -> Dict[str, any]:
        """Sample check of actual extractions"""
        sample_checks = {}

        with self.conn.cursor() as cursor:
            try:
                # Get sample of extractions
                cursor.execute("""
                    SELECT zone, permission_status, extracted_text, development_types, pattern_type
                    FROM permissibility_analysis
                    ORDER BY RANDOM()
                    LIMIT 10
                """)
                samples = cursor.fetchall()

                sample_checks['sample_count'] = len(samples)
                sample_checks['samples'] = []

                for sample in samples:
                    sample_data = {
                        'zone': sample[0],
                        'permission_status': sample[1],
                        'extracted_text': sample[2][:100] + '...' if len(sample[2]) > 100 else sample[2],
                        'development_types': sample[3],
                        'pattern_type': sample[4]
                    }
                    sample_checks['samples'].append(sample_data)

            except Exception as e:
                self.results["errors"].append(f"Error sampling extractions: {str(e)}")
                sample_checks['error'] = str(e)

        self.results["checks"]["sample_extractions"] = sample_checks
        return sample_checks

    def run_verification(self) -> bool:
        """Run all verification checks"""
        print("Verifying PRP-P1: Permissibility Pattern Extraction...")

        # Run all checks
        tables_exist = self.check_tables_exist()

        if tables_exist.get('permissibility_analysis', False):
            self.check_permissibility_data()
            self.check_data_quality()
            self.check_sample_extractions()

        # Determine overall success
        critical_passed = (
            len(self.results["errors"]) == 0 and
            tables_exist.get('permissibility_analysis', False)
        )

        self.results["success"] = critical_passed
        self.results["summary"] = {
            "total_errors": len(self.results["errors"]),
            "total_warnings": len(self.results["warnings"]),
            "critical_passed": critical_passed,
            "tables_exist": all(tables_exist.values()),
            "data_populated": self.results["checks"].get("permissibility_data", {}).get("total_extractions", 0) > 0
        }

        # Save results
        output_file = "verify_prp_p1_results.json"
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)

        # Print summary
        print("\nPRP-P1 Verification Results:")
        print(f"  Tables exist: {all(tables_exist.values())}")

        if 'permissibility_data' in self.results["checks"]:
            data = self.results["checks"]["permissibility_data"]
            print(f"  Total extractions: {data.get('total_extractions', 0)}")
            print(f"  Zone coverage: {data.get('zone_coverage', 0)}")
            print(f"  Permission types: {len(data.get('permission_types', {}))}")

        if self.results["errors"]:
            print("\nErrors found:")
            for error in self.results["errors"]:
                print(f"    - {error}")

        if self.results["warnings"]:
            print("\nWarnings:")
            for warning in self.results["warnings"]:
                print(f"    - {warning}")

        print(f"\n{'VERIFICATION PASSED' if critical_passed else 'VERIFICATION FAILED'}")
        print(f"Results saved to: {output_file}")

        return critical_passed

if __name__ == "__main__":
    verifier = PRPP1Verification()
    success = verifier.run_verification()
    sys.exit(0 if success else 1)