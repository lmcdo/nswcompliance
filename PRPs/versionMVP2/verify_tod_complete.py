#!/usr/bin/env python3
"""
Complete TOD Integration Verification Script
Runs all PRP-T1, T2, T3 verifications with comprehensive reporting
"""

import sys
import os
import subprocess
import json
import time
from typing import Dict, List, Any

class TODCompleteVerifier:
    def __init__(self):
        self.verification_scripts = [
            {
                "id": "PRP-T1",
                "name": "TOD Parking Calculator",
                "script": "verify_t1_parking_calculator.py",
                "description": "Parking reduction calculator with autocomplete"
            },
            {
                "id": "PRP-T2",
                "name": "Transport Proximity Detection",
                "script": "verify_t2_transport_detection.py",
                "description": "Transport detection and autocomplete system"
            },
            {
                "id": "PRP-T3",
                "name": "TOD Compliance Framework",
                "script": "verify_t3_compliance_framework.py",
                "description": "Comprehensive compliance assessment framework"
            }
        ]

        self.results = {}
        self.overall_status = "UNKNOWN"

    def run_individual_verification(self, script_info: Dict) -> Dict[str, Any]:
        """Run individual verification script"""
        print(f"\nRunning {script_info['name']} verification...")

        result = {
            "prp_id": script_info["id"],
            "name": script_info["name"],
            "description": script_info["description"],
            "status": "UNKNOWN",
            "execution_time": 0,
            "success_rate": 0,
            "tests_passed": 0,
            "total_tests": 0,
            "detailed_results": {},
            "error": None
        }

        try:
            start_time = time.time()

            # Run the verification script
            script_path = f"PRPs/versionMVP2/{script_info['script']}"
            cmd = [sys.executable, script_path]

            process_result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd="."
            )

            result["execution_time"] = time.time() - start_time

            # Parse results from JSON file if available
            results_file = f"PRPs/versionMVP2/{script_info['id'].lower().replace('-', '_')}_results.json"
            if os.path.exists(results_file):
                with open(results_file, 'r') as f:
                    detailed_data = json.load(f)
                    result["detailed_results"] = detailed_data
                    result["status"] = detailed_data.get("status", "UNKNOWN")
                    result["success_rate"] = detailed_data.get("success_rate", 0)
                    result["tests_passed"] = detailed_data.get("tests_passed", 0)
                    result["total_tests"] = detailed_data.get("total_tests", 0)
            else:
                # Parse from stdout/stderr
                if process_result.returncode == 0:
                    result["status"] = "PASS"
                    result["success_rate"] = 100
                else:
                    result["status"] = "FAIL"
                    result["error"] = process_result.stderr or "Unknown error"

            # Print status
            if result["status"] == "PASS":
                print(f"[PASS] {script_info['name']} - {result['success_rate']}% success")
            else:
                print(f"[FAIL] {script_info['name']} - {result.get('error', 'Failed')}")

        except subprocess.TimeoutExpired:
            result["error"] = "Verification script timeout (>5 minutes)"
            result["status"] = "TIMEOUT"
            print(f"[TIMEOUT] {script_info['name']} - Timeout")

        except Exception as e:
            result["error"] = str(e)
            result["status"] = "ERROR"
            print(f"[ERROR] {script_info['name']} - Error: {str(e)}")

        return result

    def check_prerequisite_files(self) -> Dict[str, Any]:
        """Check if all prerequisite files exist"""
        print("Checking prerequisite files...")

        required_files = {
            "services/enhanced_compliance_api.py": "Enhanced compliance API",
            "services/db_safety_wrapper.py": "Database safety wrapper",
            "frontend-nextjs/app/authoritative/page.tsx": "Authoritative page component",
            "frontend-nextjs/components/compliance/AuthoritativeComplianceDisplay.tsx": "Compliance display component"
        }

        missing_files = []
        existing_files = []

        for file_path, description in required_files.items():
            if os.path.exists(file_path):
                existing_files.append({"file": file_path, "description": description})
                print(f"[OK] {description}")
            else:
                missing_files.append({"file": file_path, "description": description})
                print(f"[MISSING] {description} - Missing: {file_path}")

        return {
            "total_required": len(required_files),
            "existing_count": len(existing_files),
            "missing_count": len(missing_files),
            "existing_files": existing_files,
            "missing_files": missing_files,
            "all_present": len(missing_files) == 0
        }

    def check_api_availability(self) -> Dict[str, Any]:
        """Check if required APIs are available"""
        print("\nChecking API availability...")

        api_endpoints = [
            "http://localhost:3007/api/property",
            "http://localhost:3007/api/compliance/live-check"
        ]

        api_status = {}
        all_available = True

        for endpoint in api_endpoints:
            try:
                import requests
                response = requests.get(endpoint, timeout=5)
                if response.status_code in [200, 404]:  # 404 is OK, means server is running
                    api_status[endpoint] = {"available": True, "status": response.status_code}
                    print(f"[OK] API available: {endpoint}")
                else:
                    api_status[endpoint] = {"available": False, "status": response.status_code}
                    print(f"[WARNING] API issues: {endpoint} - Status {response.status_code}")
                    all_available = False
            except Exception as e:
                api_status[endpoint] = {"available": False, "error": str(e)}
                print(f"[ERROR] API unavailable: {endpoint} - {str(e)}")
                all_available = False

        return {
            "all_available": all_available,
            "endpoint_status": api_status
        }

    def run_complete_verification(self) -> Dict[str, Any]:
        """Run complete TOD verification suite"""
        print("Starting Complete TOD Integration Verification")
        print("=" * 60)

        overall_start_time = time.time()

        # Step 1: Check prerequisites
        prerequisites = self.check_prerequisite_files()
        api_status = self.check_api_availability()

        # Step 2: Run individual verifications
        print(f"\nRunning {len(self.verification_scripts)} verification scripts...")

        for script_info in self.verification_scripts:
            self.results[script_info["id"]] = self.run_individual_verification(script_info)

        # Step 3: Calculate overall results
        total_execution_time = time.time() - overall_start_time

        # Aggregate results
        total_tests = sum(result.get("total_tests", 0) for result in self.results.values())
        total_passed = sum(result.get("tests_passed", 0) for result in self.results.values())
        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

        # Determine overall status
        passed_verifications = sum(1 for result in self.results.values() if result.get("status") == "PASS")
        total_verifications = len(self.verification_scripts)

        if passed_verifications == total_verifications:
            self.overall_status = "PASS"
        elif passed_verifications >= total_verifications * 0.8:  # 80% threshold
            self.overall_status = "PARTIAL_PASS"
        else:
            self.overall_status = "FAIL"

        # Compile final report
        final_report = {
            "verification_suite": "Complete TOD Integration",
            "verification_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_execution_time": round(total_execution_time, 2),
            "overall_status": self.overall_status,
            "overall_success_rate": round(overall_success_rate, 1),
            "summary": {
                "total_verifications": total_verifications,
                "passed_verifications": passed_verifications,
                "total_tests": total_tests,
                "total_passed": total_passed
            },
            "prerequisites": prerequisites,
            "api_status": api_status,
            "individual_results": self.results,
            "recommendations": self._generate_recommendations()
        }

        return final_report

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on verification results"""
        recommendations = []

        # Check individual PRP results
        failed_prps = [
            prp_id for prp_id, result in self.results.items()
            if result.get("status") != "PASS"
        ]

        if "PRP-T1" in failed_prps:
            recommendations.extend([
                "Implement TODParkingCalculator component with base parking calculations",
                "Add transport proximity integration for parking reductions",
                "Create parking calculator API endpoints"
            ])

        if "PRP-T2" in failed_prps:
            recommendations.extend([
                "Implement transport_proximity_detector.py service",
                "Add transport autocomplete API endpoints",
                "Set up transport data caching system"
            ])

        if "PRP-T3" in failed_prps:
            recommendations.extend([
                "Implement tod_compliance_checker.py and tod_rules_engine.py",
                "Add SEPP (Housing) 2021 rule interpretations",
                "Create TOD UI components and dashboard"
            ])

        # General recommendations
        if self.overall_status != "PASS":
            recommendations.extend([
                "Complete missing prerequisite files before implementing TOD features",
                "Ensure Next.js development server is running for API tests",
                "Implement comprehensive error handling for all TOD components"
            ])

        if not recommendations:
            recommendations.append("All TOD verification criteria met - ready for production deployment")

        return recommendations

    def print_summary_report(self, report: Dict[str, Any]):
        """Print comprehensive summary report"""
        print("\n" + "=" * 80)
        print("COMPLETE TOD INTEGRATION VERIFICATION SUMMARY")
        print("=" * 80)

        print(f"Overall Status: {report['overall_status']}")
        print(f"Success Rate: {report['overall_success_rate']}%")
        print(f"Execution Time: {report['total_execution_time']}s")
        print(f"Verifications: {report['summary']['passed_verifications']}/{report['summary']['total_verifications']}")
        print(f"Tests: {report['summary']['total_passed']}/{report['summary']['total_tests']}")

        print(f"\nINDIVIDUAL VERIFICATION RESULTS:")
        for prp_id, result in report['individual_results'].items():
            status_emoji = "[PASS]" if result['status'] == "PASS" else "[FAIL]"
            print(f"{status_emoji} {result['name']} ({prp_id})")
            print(f"   Status: {result['status']} | Success Rate: {result.get('success_rate', 0)}%")
            if result.get('error'):
                print(f"   Error: {result['error']}")

        print(f"\nRECOMMENDATIONS:")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"{i}. {rec}")

        print("\n" + "=" * 80)

def main():
    verifier = TODCompleteVerifier()

    # Run complete verification
    report = verifier.run_complete_verification()

    # Print summary
    verifier.print_summary_report(report)

    # Save complete report
    with open('PRPs/versionMVP2/tod_complete_verification_report.json', 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\nComplete report saved to tod_complete_verification_report.json")

    # Exit with appropriate code
    if report['overall_status'] == "PASS":
        sys.exit(0)
    elif report['overall_status'] == "PARTIAL_PASS":
        sys.exit(2)  # Partial success
    else:
        sys.exit(1)  # Failure

if __name__ == "__main__":
    main()