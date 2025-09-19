#!/usr/bin/env python3
"""
Verification script for PRP-Q1: BASIX Integration
Verifies that BASIX provisions are correctly extracted, processed, and displayed
"""

import json
import sys
import asyncio
from typing import Dict, List, Tuple
from datetime import datetime

# Add parent directory to path
sys.path.append('..')
sys.path.append('../services')

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

class BASIXIntegrationVerifier:
    """Verify BASIX integration implementation"""

    def __init__(self):
        self.results = {
            'total_checks': 0,
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'details': []
        }

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

    async def verify_planning_api_extraction(self) -> bool:
        """Verify BASIX data extraction from Planning API"""
        print(f"\n{BLUE}=== Verifying Planning API BASIX Extraction ==={RESET}")

        try:
            # Import NSW Planning API module
            from nsw_planning_api import NSWPlanningAPI

            test_address = "45 Liverpool Street, Ashfield NSW 2131"

            async with NSWPlanningAPI() as api:
                # Get property ID
                property_results = await api.lookup_property_id(test_address)
                if not property_results:
                    self.log_result(
                        "Planning API Property Lookup",
                        False,
                        "Failed to find test property"
                    )
                    return False

                prop_id = property_results[0]['propId']
                self.log_result(
                    "Planning API Property Lookup",
                    True,
                    f"Found property ID: {prop_id}"
                )

                # Get planning controls
                controls = await api.get_planning_controls(prop_id)

                # Check for Special Provisions layer
                special_provisions = None
                for control in controls:
                    if control.get('layerName') == 'Special Provisions':
                        special_provisions = control
                        break

                if not special_provisions:
                    self.log_result(
                        "Special Provisions Layer",
                        False,
                        "Special Provisions layer not found"
                    )
                    return False

                self.log_result(
                    "Special Provisions Layer",
                    True,
                    f"Found {len(special_provisions.get('results', []))} provisions"
                )

                # Check for BASIX data
                basix_found = False
                basix_climate = None
                basix_water = None

                for result in special_provisions.get('results', []):
                    if result.get('Type') == 'Climate Zones' and result.get('Map Type') == 'CLM':
                        basix_climate = result.get('Class')
                        basix_found = True
                    if 'Water Use' in str(result.get('Type', '')):
                        basix_water = result.get('Class')

                self.log_result(
                    "BASIX Climate Zone Extraction",
                    basix_climate is not None,
                    f"Climate Zone: {basix_climate}" if basix_climate else "No climate zone found",
                    {'climate_zone': basix_climate}
                )

                self.log_result(
                    "BASIX Water Zone Extraction",
                    basix_water is not None,
                    f"Water Zone: {basix_water}" if basix_water else "No water zone found (may be optional)",
                    {'water_zone': basix_water}
                )

                return basix_found

        except ImportError as e:
            self.log_result(
                "Planning API Module",
                False,
                f"Failed to import NSW Planning API module: {e}"
            )
            return False
        except Exception as e:
            self.log_result(
                "Planning API Extraction",
                False,
                f"Unexpected error: {e}"
            )
            return False

    def verify_frontend_data_flow(self) -> bool:
        """Verify frontend passes BASIX data to API"""
        print(f"\n{BLUE}=== Verifying Frontend Data Flow ==={RESET}")

        try:
            # Check if PropertySearch component exists
            import os
            component_path = '../frontend-nextjs/components/property/PropertySearch.tsx'

            if not os.path.exists(component_path):
                self.log_result(
                    "PropertySearch Component",
                    False,
                    f"Component not found at {component_path}"
                )
                return False

            # Read component and check for BASIX data handling
            with open(component_path, 'r') as f:
                content = f.read()

            # Check for BASIX provisions in payload
            has_basix_payload = 'basix_provisions' in content or 'basixProvisions' in content
            has_climate_zone = 'basixClimate' in content or 'climate_zone' in content
            has_water_zone = 'basixWater' in content or 'water_zone' in content

            self.log_result(
                "BASIX Payload Structure",
                has_basix_payload,
                "BASIX provisions in API payload" if has_basix_payload else "BASIX provisions not in payload"
            )

            self.log_result(
                "Climate Zone in Payload",
                has_climate_zone,
                "Climate zone passed to API" if has_climate_zone else "Climate zone not passed"
            )

            self.log_result(
                "Water Zone in Payload",
                has_water_zone,
                "Water zone passed to API" if has_water_zone else "Water zone not passed (may be optional)"
            )

            # Check API route for BASIX handling
            api_route_path = '../frontend-nextjs/app/api/authoritative/compliance-check/route.ts'

            if os.path.exists(api_route_path):
                with open(api_route_path, 'r') as f:
                    api_content = f.read()

                has_basix_params = 'basix_provisions' in api_content or 'basixProvisions' in api_content

                self.log_result(
                    "API Route BASIX Handling",
                    has_basix_params,
                    "API route handles BASIX parameters" if has_basix_params else "API route doesn't handle BASIX"
                )
            else:
                self.log_result(
                    "API Route File",
                    False,
                    f"API route not found at {api_route_path}"
                )

            return has_basix_payload or has_climate_zone

        except Exception as e:
            self.log_result(
                "Frontend Data Flow",
                False,
                f"Error checking frontend: {e}"
            )
            return False

    def verify_backend_processing(self) -> bool:
        """Verify backend BASIX processing"""
        print(f"\n{BLUE}=== Verifying Backend BASIX Processing ==={RESET}")

        try:
            # Check for BASIX provisions table creation
            import psycopg2
            from psycopg2.extras import RealDictCursor
            import os
            from dotenv import load_dotenv

            load_dotenv()

            # Connect to database
            conn = psycopg2.connect(
                host=os.getenv('PGHOST', 'localhost'),
                port=os.getenv('PGPORT', 5432),
                database=os.getenv('PGDATABASE', 'nsw_planning'),
                user=os.getenv('PGUSER', 'postgres'),
                password=os.getenv('PGPASSWORD', '')
            )

            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Check if BASIX provisions table exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'basix_provisions'
                )
            """)

            table_exists = cursor.fetchone()['exists']

            self.log_result(
                "BASIX Provisions Table",
                table_exists,
                "Table exists in database" if table_exists else "Table not created"
            )

            if table_exists:
                # Check if table has data
                cursor.execute("SELECT COUNT(*) as count FROM basix_provisions")
                count = cursor.fetchone()['count']

                self.log_result(
                    "BASIX Provisions Data",
                    count > 0,
                    f"Found {count} BASIX provisions" if count > 0 else "No BASIX provisions in table",
                    {'provisions_count': count}
                )

                # Check sample provision
                if count > 0:
                    cursor.execute("""
                        SELECT * FROM basix_provisions
                        WHERE climate_zone = 'Zone 17'
                        AND development_type = 'dwelling_house'
                        LIMIT 1
                    """)

                    sample = cursor.fetchone()

                    if sample:
                        self.log_result(
                            "BASIX Provision Structure",
                            True,
                            f"Zone 17 dwelling: {sample['energy_reduction_target']}% energy, {sample['water_reduction_target']}% water",
                            {'sample_provision': dict(sample)}
                        )
                    else:
                        self.log_result(
                            "BASIX Provision Structure",
                            False,
                            "No provision found for Zone 17 dwelling_house"
                        )

            conn.close()
            return table_exists

        except ImportError:
            self.log_result(
                "Database Module",
                False,
                "psycopg2 not installed - cannot verify database"
            )
            return False
        except Exception as e:
            self.log_result(
                "Backend Processing",
                False,
                f"Error checking backend: {e}"
            )
            return False

    def verify_compliance_api_integration(self) -> bool:
        """Verify BASIX integration in compliance API"""
        print(f"\n{BLUE}=== Verifying Compliance API Integration ==={RESET}")

        try:
            # Check if enhanced compliance API has BASIX handling
            api_path = '../services/enhanced_compliance_api.py'

            if not os.path.exists(api_path):
                self.log_result(
                    "Enhanced Compliance API",
                    False,
                    f"API file not found at {api_path}"
                )
                return False

            with open(api_path, 'r') as f:
                content = f.read()

            # Check for BASIX-related code
            has_basix_checker = 'BASIXComplianceChecker' in content or 'basix_requirements' in content
            has_basix_provisions = 'basix_provisions' in content
            has_climate_zone = 'climate_zone' in content

            self.log_result(
                "BASIX Compliance Checker",
                has_basix_checker,
                "BASIX checker implemented" if has_basix_checker else "BASIX checker not found"
            )

            self.log_result(
                "BASIX Provisions Handling",
                has_basix_provisions,
                "API handles BASIX provisions" if has_basix_provisions else "BASIX provisions not handled"
            )

            self.log_result(
                "Climate Zone Processing",
                has_climate_zone,
                "Climate zone processing found" if has_climate_zone else "Climate zone not processed"
            )

            return has_basix_checker or has_basix_provisions

        except Exception as e:
            self.log_result(
                "Compliance API Integration",
                False,
                f"Error checking API: {e}"
            )
            return False

    def verify_ui_display(self) -> bool:
        """Verify BASIX provisions display in UI"""
        print(f"\n{BLUE}=== Verifying UI Display Components ==={RESET}")

        try:
            # Check for BASIX display component
            component_path = '../frontend-nextjs/components/compliance/BASIXProvisions.tsx'

            component_exists = os.path.exists(component_path)

            self.log_result(
                "BASIX Display Component",
                component_exists,
                "BASIXProvisions component exists" if component_exists else "Component not created"
            )

            if component_exists:
                with open(component_path, 'r') as f:
                    content = f.read()

                # Check for required UI elements
                has_climate_display = 'climateZone' in content or 'Climate Zone' in content
                has_water_display = 'waterZone' in content or 'Water Zone' in content
                has_targets = 'numeric_value' in content or 'target' in content

                self.log_result(
                    "Climate Zone Display",
                    has_climate_display,
                    "Climate zone displayed" if has_climate_display else "Climate zone not displayed"
                )

                self.log_result(
                    "Water Zone Display",
                    has_water_display,
                    "Water zone displayed" if has_water_display else "Water zone not displayed"
                )

                self.log_result(
                    "BASIX Targets Display",
                    has_targets,
                    "Numeric targets displayed" if has_targets else "Targets not displayed"
                )

            # Check if main compliance display includes BASIX
            main_display_path = '../frontend-nextjs/components/compliance/AuthoritativeComplianceDisplay.tsx'

            if os.path.exists(main_display_path):
                with open(main_display_path, 'r') as f:
                    content = f.read()

                has_basix_integration = 'BASIXProvisions' in content or 'basix_provisions' in content

                self.log_result(
                    "BASIX in Main Display",
                    has_basix_integration,
                    "BASIX integrated in main display" if has_basix_integration else "BASIX not in main display"
                )

            return component_exists

        except Exception as e:
            self.log_result(
                "UI Display Verification",
                False,
                f"Error checking UI: {e}"
            )
            return False

    async def run_verification(self):
        """Run all verification checks"""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}PRP-Q1: BASIX Integration Verification{RESET}")
        print(f"{BLUE}{'='*60}{RESET}")

        # Run all checks
        api_ok = await self.verify_planning_api_extraction()
        frontend_ok = self.verify_frontend_data_flow()
        backend_ok = self.verify_backend_processing()
        compliance_ok = self.verify_compliance_api_integration()
        ui_ok = self.verify_ui_display()

        # Generate summary
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}VERIFICATION SUMMARY{RESET}")
        print(f"{BLUE}{'='*60}{RESET}")

        print(f"\nTotal Checks: {self.results['total_checks']}")
        print(f"{GREEN}Passed: {self.results['passed']}{RESET}")
        print(f"{RED}Failed: {self.results['failed']}{RESET}")

        if self.results['warnings'] > 0:
            print(f"{YELLOW}Warnings: {self.results['warnings']}{RESET}")

        # Overall status
        overall_pass = self.results['failed'] == 0

        print(f"\n{BLUE}Overall Status: {RESET}", end='')
        if overall_pass:
            print(f"{GREEN}✓ VERIFICATION PASSED{RESET}")
        else:
            print(f"{RED}✗ VERIFICATION FAILED{RESET}")

        # Critical path status
        print(f"\n{BLUE}Critical Path Status:{RESET}")
        print(f"  1. API Extraction: {'✓' if api_ok else '✗'}")
        print(f"  2. Frontend Flow: {'✓' if frontend_ok else '✗'}")
        print(f"  3. Backend Processing: {'✓' if backend_ok else '✗'}")
        print(f"  4. Compliance Integration: {'✓' if compliance_ok else '✗'}")
        print(f"  5. UI Display: {'✓' if ui_ok else '✗'}")

        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'basix_verification_{timestamp}.json'

        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)

        print(f"\n{BLUE}Results saved to: {output_file}{RESET}")

        # Implementation recommendations
        if not overall_pass:
            print(f"\n{YELLOW}IMPLEMENTATION RECOMMENDATIONS:{RESET}")

            if not api_ok:
                print("  • Verify NSW Planning API connection and test property")

            if not frontend_ok:
                print("  • Update PropertySearch component to pass BASIX data")
                print("  • Modify API route to accept BASIX provisions")

            if not backend_ok:
                print("  • Create basix_provisions table in database")
                print("  • Populate with BASIX requirements data")

            if not compliance_ok:
                print("  • Implement BASIXComplianceChecker class")
                print("  • Add BASIX processing to enhanced_compliance_api.py")

            if not ui_ok:
                print("  • Create BASIXProvisions display component")
                print("  • Integrate BASIX display in main compliance view")

        return overall_pass

if __name__ == "__main__":
    verifier = BASIXIntegrationVerifier()
    success = asyncio.run(verifier.run_verification())
    sys.exit(0 if success else 1)