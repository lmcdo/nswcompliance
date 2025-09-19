#!/usr/bin/env python3
"""
Verification script for PRP-Q2: Special Provisions Processing Engine
Verifies that special provisions are correctly extracted, processed, tiered, and displayed
"""

import json
import sys
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

# Add parent directory to path
sys.path.append('..')
sys.path.append('../services')

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
MAGENTA = '\033[95m'
RESET = '\033[0m'

class SpecialProvisionsVerifier:
    """Verify special provisions processing implementation"""

    def __init__(self):
        self.results = {
            'total_checks': 0,
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'provision_types': {},
            'tier_distribution': {},
            'details': []
        }
        self.db_conn = None

    def connect_database(self) -> bool:
        """Connect to PostgreSQL database"""
        try:
            import os
            from dotenv import load_dotenv
            load_dotenv()

            self.db_conn = psycopg2.connect(
                host=os.getenv('PGHOST', 'localhost'),
                port=os.getenv('PGPORT', 5432),
                database=os.getenv('PGDATABASE', 'nsw_planning'),
                user=os.getenv('PGUSER', 'postgres'),
                password=os.getenv('PGPASSWORD', '')
            )
            return True
        except Exception as e:
            print(f"{RED}Database connection failed: {e}{RESET}")
            return False

    def log_result(self, check_name: str, passed: bool, message: str, data: Dict = None):
        """Log verification result"""
        self.results['total_checks'] += 1

        if passed:
            self.results['passed'] += 1
            status = f"{GREEN}✓ PASS{RESET}"
        else:
            self.results['failed'] += 1
            status = f"{RED}✗ FAIL{RESET}"

        print(f"{status} {check_name}: {message}")

        self.results['details'].append({
            'check': check_name,
            'passed': passed,
            'message': message,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })

    async def verify_api_extraction(self) -> Dict:
        """Verify extraction of special provisions from Planning API"""
        print(f"\n{BLUE}=== Verifying Special Provisions Extraction ==={RESET}")

        provision_types = set()
        sample_provisions = []

        try:
            from nsw_planning_api import NSWPlanningAPI

            test_addresses = [
                "45 Liverpool Street, Ashfield NSW 2131",
                "10 Hunter Street, Lewisham NSW 2049",
                "25 Station Street, Marrickville NSW 2204"
            ]

            async with NSWPlanningAPI() as api:
                for address in test_addresses:
                    print(f"\n  Testing: {address}")

                    property_results = await api.lookup_property_id(address)
                    if not property_results:
                        continue

                    prop_id = property_results[0]['propId']
                    controls = await api.get_planning_controls(prop_id)

                    # Find Special Provisions layer
                    for control in controls:
                        if control.get('layerName') == 'Special Provisions':
                            provisions = control.get('results', [])

                            for provision in provisions:
                                prov_type = provision.get('Type', 'Unknown')
                                provision_types.add(prov_type)

                                # Collect sample of each type
                                if prov_type not in [p['Type'] for p in sample_provisions]:
                                    sample_provisions.append(provision)

                            self.log_result(
                                f"Property {prop_id}",
                                True,
                                f"Found {len(provisions)} special provisions"
                            )

            # Verify known provision types
            expected_types = [
                'Climate Zones',
                'State Environmental Planning Policy',
                'Flood Planning',
                'Bushfire Prone Land',
                'Acid Sulfate Soils'
            ]

            for expected in expected_types:
                found = any(expected in pt for pt in provision_types)
                self.log_result(
                    f"Provision Type: {expected}",
                    found,
                    "Found in API data" if found else "Not found in test properties"
                )

            self.results['provision_types'] = list(provision_types)

            return {
                'types_found': len(provision_types),
                'samples': sample_provisions
            }

        except ImportError as e:
            self.log_result(
                "NSW Planning API",
                False,
                f"Module import failed: {e}"
            )
            return {}
        except Exception as e:
            self.log_result(
                "API Extraction",
                False,
                f"Unexpected error: {e}"
            )
            return {}

    def verify_database_schema(self) -> bool:
        """Verify special provisions database schema"""
        print(f"\n{BLUE}=== Verifying Database Schema ==={RESET}")

        if not self.db_conn:
            if not self.connect_database():
                return False

        cursor = self.db_conn.cursor(cursor_factory=RealDictCursor)

        # Check required tables
        tables = [
            'special_provisions_registry',
            'provision_thresholds',
            'provision_implications'
        ]

        all_exist = True
        for table in tables:
            cursor.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = '{table}'
                )
            """)
            exists = cursor.fetchone()['exists']

            self.log_result(
                f"Table: {table}",
                exists,
                "Exists" if exists else "Not created"
            )

            if not exists:
                all_exist = False

        # Check registry data if table exists
        if all_exist:
            cursor.execute("""
                SELECT COUNT(*) as count,
                       COUNT(DISTINCT provision_type) as types
                FROM special_provisions_registry
                WHERE active = TRUE
            """)
            result = cursor.fetchone()

            self.log_result(
                "Registry Data",
                result['count'] > 0,
                f"{result['count']} provisions, {result['types']} types" if result['count'] > 0
                else "No provisions registered",
                {'count': result['count'], 'types': result['types']}
            )

            # Check tier distribution
            cursor.execute("""
                SELECT default_tier_level, COUNT(*) as count
                FROM special_provisions_registry
                WHERE active = TRUE
                GROUP BY default_tier_level
                ORDER BY default_tier_level
            """)

            tier_dist = {f"tier_{row['default_tier_level']}": row['count']
                        for row in cursor.fetchall()}

            self.results['tier_distribution'] = tier_dist

            self.log_result(
                "Tier Distribution",
                len(tier_dist) > 0,
                f"Provisions across {len(tier_dist)} tiers",
                tier_dist
            )

        return all_exist

    def verify_processing_engine(self) -> bool:
        """Verify special provisions processing engine"""
        print(f"\n{BLUE}=== Verifying Processing Engine ==={RESET}")

        try:
            # Check if processing engine exists
            import os
            engine_path = '../services/provisions_processing_engine.py'

            if not os.path.exists(engine_path):
                # Try alternative path
                engine_path = '../services/special_provisions_processor.py'

            engine_exists = os.path.exists(engine_path)

            self.log_result(
                "Processing Engine File",
                engine_exists,
                f"Found at {engine_path}" if engine_exists else "Engine file not found"
            )

            if engine_exists:
                with open(engine_path, 'r') as f:
                    content = f.read()

                # Check for key components
                has_engine_class = 'SpecialProvisionsEngine' in content or 'ProvisionsProcessor' in content
                has_process_method = 'process_provisions' in content
                has_tier_assignment = 'tier_level' in content
                has_sepp_processing = 'process_sepp' in content or '_process_sepp' in content
                has_hazard_processing = 'flood' in content.lower() or 'bushfire' in content.lower()

                self.log_result(
                    "Engine Class",
                    has_engine_class,
                    "Processing engine class found" if has_engine_class else "Class not found"
                )

                self.log_result(
                    "Process Method",
                    has_process_method,
                    "process_provisions method found" if has_process_method else "Method not found"
                )

                self.log_result(
                    "Tier Assignment Logic",
                    has_tier_assignment,
                    "Tier level assignment found" if has_tier_assignment else "No tier assignment"
                )

                self.log_result(
                    "SEPP Processing",
                    has_sepp_processing,
                    "SEPP processing logic found" if has_sepp_processing else "SEPP processing not found"
                )

                self.log_result(
                    "Hazard Processing",
                    has_hazard_processing,
                    "Hazard processing found" if has_hazard_processing else "Hazard processing not found"
                )

                return has_engine_class and has_process_method

            return False

        except Exception as e:
            self.log_result(
                "Processing Engine",
                False,
                f"Error checking engine: {e}"
            )
            return False

    def verify_provision_mapping(self) -> bool:
        """Verify provision type to tier mapping"""
        print(f"\n{BLUE}=== Verifying Provision Mapping ==={RESET}")

        # Test mappings
        test_mappings = [
            ('Climate Zones', 1, "BASIX should be Tier 1"),
            ('Flood Planning', 1, "Flood hazards should be Tier 1"),
            ('Bushfire Prone Land', 1, "Bushfire should be Tier 1"),
            ('Acid Sulfate Soils', 2, "ASS should be Tier 2"),
            ('Heritage', 2, "Heritage should be Tier 2")
        ]

        if not self.db_conn:
            if not self.connect_database():
                return False

        cursor = self.db_conn.cursor(cursor_factory=RealDictCursor)

        all_correct = True
        for provision_type, expected_tier, description in test_mappings:
            cursor.execute("""
                SELECT default_tier_level, authority_level
                FROM special_provisions_registry
                WHERE provision_type = %s
            """, (provision_type,))

            result = cursor.fetchone()

            if result:
                tier_correct = result['default_tier_level'] == expected_tier
                self.log_result(
                    f"{provision_type} Tier",
                    tier_correct,
                    f"Tier {result['default_tier_level']} - {description}",
                    {'expected': expected_tier, 'actual': result['default_tier_level']}
                )
                if not tier_correct:
                    all_correct = False
            else:
                self.log_result(
                    f"{provision_type} Mapping",
                    False,
                    f"Not found in registry - {description}"
                )
                all_correct = False

        return all_correct

    def verify_integration_layer(self) -> bool:
        """Verify integration with compliance API"""
        print(f"\n{BLUE}=== Verifying Integration Layer ==={RESET}")

        try:
            # Check integration service
            integration_path = '../services/provisions_integration.py'
            api_path = '../services/enhanced_compliance_api.py'

            integration_exists = os.path.exists(integration_path)

            if not integration_exists:
                # Check if integrated directly in API
                if os.path.exists(api_path):
                    with open(api_path, 'r') as f:
                        api_content = f.read()

                    has_provisions = 'special_provisions' in api_content
                    has_processing = 'process_provisions' in api_content or 'SpecialProvisionsProcessor' in api_content

                    self.log_result(
                        "Provisions in API",
                        has_provisions,
                        "Special provisions handled in API" if has_provisions else "Not in API"
                    )

                    self.log_result(
                        "Processing Logic",
                        has_processing,
                        "Processing logic found" if has_processing else "Processing not found"
                    )

                    return has_provisions or has_processing
            else:
                self.log_result(
                    "Integration Service",
                    True,
                    f"Found at {integration_path}"
                )

                with open(integration_path, 'r') as f:
                    content = f.read()

                has_integration = 'ProvisionsIntegrationService' in content
                has_merge = 'merge_with_hierarchy' in content

                self.log_result(
                    "Integration Class",
                    has_integration,
                    "Integration service class found" if has_integration else "Class not found"
                )

                self.log_result(
                    "Hierarchy Merge",
                    has_merge,
                    "Hierarchy merge logic found" if has_merge else "Merge not found"
                )

                return has_integration

            return False

        except Exception as e:
            self.log_result(
                "Integration Layer",
                False,
                f"Error checking integration: {e}"
            )
            return False

    def verify_ui_components(self) -> bool:
        """Verify UI components for special provisions"""
        print(f"\n{BLUE}=== Verifying UI Components ==={RESET}")

        try:
            # Check for special provisions display in main component
            main_display = '../frontend-nextjs/components/compliance/AuthoritativeComplianceDisplay.tsx'

            if os.path.exists(main_display):
                with open(main_display, 'r') as f:
                    content = f.read()

                has_special = 'special_provisions' in content or 'specialProvisions' in content
                has_hazards = 'hazard' in content.lower()
                has_environmental = 'environmental' in content.lower()

                self.log_result(
                    "Special Provisions Display",
                    has_special,
                    "Special provisions in display" if has_special else "Not in display"
                )

                self.log_result(
                    "Hazard Display",
                    has_hazards,
                    "Hazard assessments shown" if has_hazards else "Hazards not shown"
                )

                self.log_result(
                    "Environmental Display",
                    has_environmental,
                    "Environmental constraints shown" if has_environmental else "Not shown"
                )

                return has_special

            else:
                self.log_result(
                    "Display Component",
                    False,
                    "AuthoritativeComplianceDisplay not found"
                )
                return False

        except Exception as e:
            self.log_result(
                "UI Components",
                False,
                f"Error checking UI: {e}"
            )
            return False

    def test_provision_processing(self) -> bool:
        """Test actual provision processing with sample data"""
        print(f"\n{BLUE}=== Testing Provision Processing ==={RESET}")

        # Sample provisions from API
        test_provisions = [
            {
                'Type': 'Climate Zones',
                'Map Type': 'CLM',
                'Class': 'Zone 17'
            },
            {
                'Type': 'State Environmental Planning Policy',
                'EPI Name': 'SEPP (Housing) 2021',
                'Legislative Clause': '3.31'
            },
            {
                'Type': 'Flood Planning',
                'Category': 'Flood Planning Area',
                'Level': '1:100 Year'
            },
            {
                'Type': 'Bushfire Prone Land',
                'Category': 'Vegetation Category 1',
                'Buffer': '100m'
            },
            {
                'Type': 'Acid Sulfate Soils',
                'Class': 'Class 2',
                'Action': 'Works below 2m AHD'
            }
        ]

        try:
            # Try to import and test the processing engine
            sys.path.append('../services')

            # Try different module names
            engine = None
            try:
                from provisions_processing_engine import SpecialProvisionsEngine
                if self.db_conn:
                    engine = SpecialProvisionsEngine(self.db_conn)
            except ImportError:
                try:
                    from special_provisions_processor import SpecialProvisionsProcessor
                    engine = SpecialProvisionsProcessor()
                except ImportError:
                    pass

            if engine:
                # Process test provisions
                results = engine.process_provisions(
                    test_provisions,
                    'R4',
                    'dwelling_house'
                )

                # Check results
                total_processed = results.get('metadata', {}).get('total_processed', 0)

                self.log_result(
                    "Processing Test",
                    total_processed > 0,
                    f"Processed {total_processed} provisions",
                    {'processed': total_processed}
                )

                # Check tier distribution
                for tier in range(1, 6):
                    tier_key = f'tier_{tier}_provisions'
                    count = len(results.get(tier_key, []))
                    if count > 0:
                        print(f"  {MAGENTA}Tier {tier}: {count} provisions{RESET}")

                # Check hazard assessments
                hazards = results.get('hazard_assessments', [])
                self.log_result(
                    "Hazard Assessments",
                    len(hazards) > 0,
                    f"Generated {len(hazards)} hazard assessments" if hazards
                    else "No hazard assessments"
                )

                return total_processed > 0
            else:
                self.log_result(
                    "Processing Engine Import",
                    False,
                    "Could not import processing engine"
                )
                return False

        except Exception as e:
            self.log_result(
                "Processing Test",
                False,
                f"Error testing processing: {e}"
            )
            return False

    async def run_verification(self):
        """Run all verification checks"""
        print(f"\n{BLUE}{'='*70}{RESET}")
        print(f"{BLUE}PRP-Q2: Special Provisions Processing Engine Verification{RESET}")
        print(f"{BLUE}{'='*70}{RESET}")

        # Run all checks
        extraction_data = await self.verify_api_extraction()
        schema_ok = self.verify_database_schema()
        engine_ok = self.verify_processing_engine()
        mapping_ok = self.verify_provision_mapping()
        integration_ok = self.verify_integration_layer()
        ui_ok = self.verify_ui_components()
        processing_ok = self.test_provision_processing()

        # Close database connection
        if self.db_conn:
            self.db_conn.close()

        # Generate summary
        print(f"\n{BLUE}{'='*70}{RESET}")
        print(f"{BLUE}VERIFICATION SUMMARY{RESET}")
        print(f"{BLUE}{'='*70}{RESET}")

        print(f"\nTotal Checks: {self.results['total_checks']}")
        print(f"{GREEN}Passed: {self.results['passed']}{RESET}")
        print(f"{RED}Failed: {self.results['failed']}{RESET}")

        # Overall status
        overall_pass = self.results['failed'] == 0

        print(f"\n{BLUE}Overall Status: {RESET}", end='')
        if overall_pass:
            print(f"{GREEN}✓ VERIFICATION PASSED{RESET}")
        else:
            print(f"{RED}✗ VERIFICATION FAILED{RESET}")

        # Component status
        print(f"\n{BLUE}Component Status:{RESET}")
        print(f"  1. API Extraction: {'✓' if extraction_data else '✗'}")
        print(f"  2. Database Schema: {'✓' if schema_ok else '✗'}")
        print(f"  3. Processing Engine: {'✓' if engine_ok else '✗'}")
        print(f"  4. Provision Mapping: {'✓' if mapping_ok else '✗'}")
        print(f"  5. Integration Layer: {'✓' if integration_ok else '✗'}")
        print(f"  6. UI Components: {'✓' if ui_ok else '✗'}")
        print(f"  7. Processing Test: {'✓' if processing_ok else '✗'}")

        # Provision types found
        if self.results['provision_types']:
            print(f"\n{BLUE}Provision Types Found:{RESET}")
            for ptype in self.results['provision_types']:
                print(f"  • {ptype}")

        # Tier distribution
        if self.results['tier_distribution']:
            print(f"\n{BLUE}Tier Distribution:{RESET}")
            for tier, count in sorted(self.results['tier_distribution'].items()):
                print(f"  • {tier}: {count} provisions")

        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'special_provisions_verification_{timestamp}.json'

        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)

        print(f"\n{BLUE}Results saved to: {output_file}{RESET}")

        # Implementation recommendations
        if not overall_pass:
            print(f"\n{YELLOW}IMPLEMENTATION RECOMMENDATIONS:{RESET}")

            if not schema_ok:
                print("  • Create special provisions database tables")
                print("  • Populate provision registry with known types")

            if not engine_ok:
                print("  • Implement SpecialProvisionsEngine class")
                print("  • Add processing logic for each provision type")

            if not mapping_ok:
                print("  • Correct tier assignments in registry")
                print("  • Ensure hazards are Tier 1, guidance is Tier 4")

            if not integration_ok:
                print("  • Create integration service or add to API")
                print("  • Implement hierarchy merge logic")

            if not ui_ok:
                print("  • Add special provisions display to UI")
                print("  • Show hazard assessments prominently")

            if not processing_ok:
                print("  • Test processing engine with real data")
                print("  • Verify tier assignments are correct")

        return overall_pass

if __name__ == "__main__":
    import os
    verifier = SpecialProvisionsVerifier()
    success = asyncio.run(verifier.run_verification())
    sys.exit(0 if success else 1)