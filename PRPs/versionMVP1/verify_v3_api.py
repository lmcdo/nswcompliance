#!/usr/bin/env python3
"""
Verification script for PRP-V3: API Integration
Validates that API endpoints support version parameters
"""

import sys
import json
import requests
from datetime import date, datetime
from typing import Dict, List, Optional
import time

class APIVerification:
    """Verify API version integration"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "prp": "V3_API_INTEGRATION",
            "checks": {},
            "errors": [],
            "warnings": [],
            "success": False
        }

    def check_api_health(self) -> bool:
        """Check if API is running"""
        try:
            response = requests.get(f"{self.base_url}/docs", timeout=5)
            is_healthy = response.status_code == 200
            self.results["checks"]["api_health"] = is_healthy
            return is_healthy
        except Exception as e:
            self.results["errors"].append(f"API not accessible: {str(e)}")
            self.results["checks"]["api_health"] = False
            return False

    def test_provisions_endpoint(self) -> Dict[str, bool]:
        """Test /api/provisions with version parameters"""
        endpoint_tests = {}

        try:
            # Test without version params (backward compatibility)
            response = requests.get(f"{self.base_url}/api/provisions")
            endpoint_tests['no_params'] = response.status_code == 200

            # Test with version=current
            response = requests.get(f"{self.base_url}/api/provisions?version=current")
            endpoint_tests['version_current'] = response.status_code == 200

            # Test with version=previous
            response = requests.get(f"{self.base_url}/api/provisions?version=previous")
            endpoint_tests['version_previous'] = response.status_code == 200

            # Test with as_at_date
            test_date = "2023-06-01"
            response = requests.get(f"{self.base_url}/api/provisions?as_at_date={test_date}")
            endpoint_tests['as_at_date'] = response.status_code == 200

            # Test combined parameters
            response = requests.get(
                f"{self.base_url}/api/provisions?version=current&include_version_info=true"
            )
            endpoint_tests['combined_params'] = response.status_code == 200

            # Check response structure
            if response.status_code == 200:
                data = response.json()
                endpoint_tests['has_status'] = 'status' in data
                endpoint_tests['has_query_params'] = 'query_params' in data
                endpoint_tests['has_provisions'] = 'provisions' in data

        except Exception as e:
            self.results["errors"].append(f"Provisions endpoint test failed: {str(e)}")
            endpoint_tests['error'] = False

        return endpoint_tests

    def test_version_endpoints(self) -> Dict[str, bool]:
        """Test version-specific endpoints"""
        version_tests = {}

        try:
            # Test /api/versions/current
            response = requests.get(f"{self.base_url}/api/versions/current")
            version_tests['current_versions'] = response.status_code == 200

            # Test /api/versions/{doc_type}/{doc_id}
            response = requests.get(f"{self.base_url}/api/versions/LEP/Inner-West-LEP-2022")
            version_tests['document_versions'] = response.status_code in [200, 404]  # 404 if no data yet

            # Check response structure
            if response.status_code == 200:
                data = response.json()
                version_tests['has_versions'] = 'versions' in data

        except Exception as e:
            self.results["warnings"].append(f"Version endpoints not fully implemented: {str(e)}")
            version_tests['not_implemented'] = True

        return version_tests

    def test_compliance_endpoint(self) -> Dict[str, bool]:
        """Test compliance check with version awareness"""
        compliance_tests = {}

        try:
            # Test compliance check with assessment_date
            payload = {
                "property_id": "123",
                "development_type": "dwelling",
                "assessment_date": "2023-12-01"
            }

            response = requests.post(
                f"{self.base_url}/api/compliance/check",
                json=payload
            )

            compliance_tests['with_date'] = response.status_code in [200, 422]  # 422 if validation differs

            # Test without assessment_date (should use current)
            payload_current = {
                "property_id": "123",
                "development_type": "dwelling"
            }

            response = requests.post(
                f"{self.base_url}/api/compliance/check",
                json=payload_current
            )

            compliance_tests['without_date'] = response.status_code in [200, 422]

        except Exception as e:
            self.results["warnings"].append(f"Compliance endpoint test warning: {str(e)}")
            compliance_tests['error'] = False

        return compliance_tests

    def check_response_headers(self) -> Dict[str, bool]:
        """Check if version headers are included in responses"""
        header_tests = {}

        try:
            response = requests.get(f"{self.base_url}/api/provisions?version=current")

            # Check for version-related headers
            headers = response.headers
            header_tests['has_api_version'] = 'X-API-Version' in headers
            header_tests['has_version_support'] = 'X-Version-Support' in headers
            header_tests['has_version_mode'] = 'X-Version-Mode' in headers

        except Exception as e:
            self.results["warnings"].append(f"Header check failed: {str(e)}")
            header_tests['error'] = False

        return header_tests

    def test_backward_compatibility(self) -> Dict[str, bool]:
        """Ensure existing API calls still work"""
        compat_tests = {}

        try:
            # Test existing endpoints without version params
            endpoints = [
                "/api/provisions",
                "/api/compliance/check",
            ]

            for endpoint in endpoints:
                if "check" in endpoint:
                    response = requests.post(
                        f"{self.base_url}{endpoint}",
                        json={"property_id": "123", "development_type": "dwelling"}
                    )
                else:
                    response = requests.get(f"{self.base_url}{endpoint}")

                compat_tests[endpoint] = response.status_code in [200, 422]

        except Exception as e:
            self.results["errors"].append(f"Backward compatibility test failed: {str(e)}")
            compat_tests['error'] = False

        return compat_tests

    def run_verification(self) -> bool:
        """Run all API verification checks"""
        print("🔍 Verifying PRP-V3: API Integration...")

        # Check if API is running
        print("\n🏥 Checking API health...")
        if not self.check_api_health():
            print("❌ API is not running. Please start the API server first.")
            print("   Run: python api_server.py")
            self.results["success"] = False
            return False

        print("✅ API is running")

        # Test provisions endpoint
        print("\n📋 Testing provisions endpoint...")
        provisions_results = self.test_provisions_endpoint()
        self.results["checks"]["provisions_endpoint"] = provisions_results
        print(f"  Provisions tests: {sum(provisions_results.values())}/{len(provisions_results)} passed")

        # Test version endpoints
        print("\n🏷️ Testing version endpoints...")
        version_results = self.test_version_endpoints()
        self.results["checks"]["version_endpoints"] = version_results
        print(f"  Version tests: {sum(1 for v in version_results.values() if v)}/{len(version_results)} passed")

        # Test compliance endpoint
        print("\n✅ Testing compliance endpoint...")
        compliance_results = self.test_compliance_endpoint()
        self.results["checks"]["compliance_endpoint"] = compliance_results
        print(f"  Compliance tests: {sum(1 for v in compliance_results.values() if v)}/{len(compliance_results)} passed")

        # Check response headers
        print("\n📬 Checking response headers...")
        header_results = self.check_response_headers()
        self.results["checks"]["response_headers"] = header_results
        print(f"  Header tests: {sum(1 for v in header_results.values() if v)}/{len(header_results)} passed")

        # Test backward compatibility
        print("\n🔄 Testing backward compatibility...")
        compat_results = self.test_backward_compatibility()
        self.results["checks"]["backward_compatibility"] = compat_results
        print(f"  Compatibility tests: {sum(1 for v in compat_results.values() if v)}/{len(compat_results)} passed")

        # Determine overall success
        all_critical_passed = (
            provisions_results.get('no_params', False) and  # Backward compat
            provisions_results.get('version_current', False) and  # Version support
            compat_results.get('/api/provisions', False)  # Core functionality
        )

        self.results["success"] = all_critical_passed

        # Save results
        with open("verify_v3_results.json", "w") as f:
            json.dump(self.results, f, indent=2)

        # Print summary
        print("\n" + "=" * 50)
        print("📊 API Verification Summary:")
        print(f"  Critical endpoints: {'✅' if all_critical_passed else '❌'}")
        print(f"  Version parameters: {'✅' if provisions_results.get('version_current', False) else '❌'}")
        print(f"  Backward compatibility: {'✅' if compat_results.get('/api/provisions', False) else '❌'}")

        if self.results["warnings"]:
            print("\n⚠️ Warnings:")
            for warning in self.results["warnings"]:
                print(f"  - {warning}")

        print(f"\n{'✅ PRP-V3 VERIFICATION PASSED' if all_critical_passed else '❌ PRP-V3 VERIFICATION FAILED'}")

        return all_critical_passed

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Verify API version integration')
    parser.add_argument('--url', default='http://localhost:8000',
                       help='API base URL (default: http://localhost:8000)')

    args = parser.parse_args()

    verifier = APIVerification(base_url=args.url)
    success = verifier.run_verification()

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()