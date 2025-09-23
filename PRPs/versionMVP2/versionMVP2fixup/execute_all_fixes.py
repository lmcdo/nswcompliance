#!/usr/bin/env python3
"""
Master Execution Script for Version MVP2 Fixup PRPs
Executes all fixup PRPs in correct order with dependency management
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from typing import Dict, List, Any

class FixupMasterExecution:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "objective": "Execute all Version MVP2 fixup PRPs",
            "overall_success": False,
            "prps_executed": [],
            "prps_passed": [],
            "prps_failed": [],
            "execution_time": None
        }

        self.prps = [
            {
                "id": "F1",
                "name": "Foreign Key Constraint Fix",
                "script": "verify_f1_foreign_key_fix.py",
                "description": "Fix V5 foreign key constraint errors in provision_changes",
                "dependencies": []
            },
            {
                "id": "F2",
                "name": "Metadata Validation Fix",
                "script": "verify_f2_metadata_validation.py",
                "description": "Fix V7 Pydantic metadata validation issues",
                "dependencies": []
            },
            {
                "id": "F3",
                "name": "API Port Detection Fix",
                "script": "verify_f3_api_port_detection.py",
                "description": "Fix API port detection for verification scripts",
                "dependencies": []
            },
            {
                "id": "F4",
                "name": "Provision Linking Completion",
                "script": "verify_f4_provision_linking.py",
                "description": "Complete linking of remaining 10K provisions to versions",
                "dependencies": ["F1", "F2"]  # Needs database fixes first
            }
        ]

    def check_prerequisites(self) -> bool:
        """Check system prerequisites before execution"""
        print("Checking prerequisites...")

        # Check if we're in the right directory
        if not os.path.exists("verify_f1_foreign_key_fix.py"):
            print("  ERROR: Not in versionMVP2fixup directory")
            return False

        # Check database connectivity
        try:
            import psycopg2
            conn = psycopg2.connect(
                host="127.0.0.1",
                database="nsw_planning",
                user="postgres",
                port=5432
            )
            conn.close()
            print("  Database connectivity: OK")
        except Exception as e:
            print(f"  Database connectivity: FAILED - {str(e)}")
            return False

        # Check Python dependencies
        required_modules = ["psycopg2", "requests", "json", "datetime"]
        for module in required_modules:
            try:
                __import__(module)
                print(f"  Module {module}: OK")
            except ImportError:
                print(f"  Module {module}: MISSING")
                return False

        print("  Prerequisites check: PASSED")
        return True

    def execute_prp(self, prp: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single PRP and return results"""
        print(f"\n{'=' * 60}")
        print(f"Executing PRP-{prp['id']}: {prp['name']}")
        print(f"{'=' * 60}")

        start_time = datetime.now()

        try:
            # Run the verification script
            result = subprocess.run(
                [sys.executable, prp["script"]],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )

            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()

            # Parse results
            success = result.returncode == 0
            output = result.stdout
            error_output = result.stderr

            print(f"Execution completed in {execution_time:.1f} seconds")
            print(f"Return code: {result.returncode}")

            # Try to load JSON results if available
            results_file = f"verify_{prp['id'].lower()}_results.json"
            detailed_results = {}
            if os.path.exists(results_file):
                try:
                    with open(results_file, 'r') as f:
                        detailed_results = json.load(f)
                except Exception as e:
                    print(f"Warning: Could not load results file {results_file}: {str(e)}")

            execution_result = {
                "prp_id": prp["id"],
                "prp_name": prp["name"],
                "success": success,
                "execution_time": execution_time,
                "return_code": result.returncode,
                "stdout": output,
                "stderr": error_output,
                "detailed_results": detailed_results,
                "timestamp": start_time.isoformat()
            }

            # Print summary
            if success:
                print(f"PRP-{prp['id']} PASSED")
                self.results["prps_passed"].append(prp["id"])
            else:
                print(f"PRP-{prp['id']} FAILED")
                self.results["prps_failed"].append(prp["id"])
                if error_output:
                    print(f"Error output: {error_output}")

            return execution_result

        except subprocess.TimeoutExpired:
            print(f"PRP-{prp['id']} TIMED OUT (10 minutes)")
            self.results["prps_failed"].append(prp["id"])
            return {
                "prp_id": prp["id"],
                "prp_name": prp["name"],
                "success": False,
                "error": "Execution timeout",
                "execution_time": 600,
                "timestamp": start_time.isoformat()
            }

        except Exception as e:
            print(f"PRP-{prp['id']} EXECUTION ERROR: {str(e)}")
            self.results["prps_failed"].append(prp["id"])
            return {
                "prp_id": prp["id"],
                "prp_name": prp["name"],
                "success": False,
                "error": str(e),
                "execution_time": 0,
                "timestamp": start_time.isoformat()
            }

    def can_execute_prp(self, prp: Dict[str, Any], completed_prps: List[str]) -> bool:
        """Check if PRP dependencies are satisfied"""
        for dependency in prp.get("dependencies", []):
            if dependency not in completed_prps:
                return False
        return True

    def execute_all_prps(self) -> bool:
        """Execute all PRPs in dependency order"""
        print("Starting Version MVP2 Fixup PRP Execution...")
        print(f"Total PRPs to execute: {len(self.prps)}")

        start_time = datetime.now()
        completed_prps = []
        remaining_prps = self.prps.copy()

        while remaining_prps:
            # Find PRPs that can be executed (dependencies satisfied)
            executable_prps = [
                prp for prp in remaining_prps
                if self.can_execute_prp(prp, completed_prps)
            ]

            if not executable_prps:
                print("ERROR: Circular dependency or unmet dependencies detected!")
                for prp in remaining_prps:
                    print(f"  {prp['id']} waiting for: {prp.get('dependencies', [])}")
                return False

            # Execute the first executable PRP
            prp = executable_prps[0]
            execution_result = self.execute_prp(prp)
            self.results["prps_executed"].append(execution_result)

            if execution_result["success"]:
                completed_prps.append(prp["id"])

            # Remove from remaining list regardless of success
            # (to avoid infinite loops, but track failures)
            remaining_prps.remove(prp)

        end_time = datetime.now()
        total_execution_time = (end_time - start_time).total_seconds()
        self.results["execution_time"] = total_execution_time

        # Determine overall success
        overall_success = len(self.results["prps_failed"]) == 0

        self.results["overall_success"] = overall_success

        return overall_success

    def print_final_summary(self):
        """Print final execution summary"""
        print("\n" + "=" * 80)
        print("VERSION MVP2 FIXUP PRP EXECUTION SUMMARY")
        print("=" * 80)

        print(f"Total execution time: {self.results.get('execution_time', 0):.1f} seconds")
        print(f"PRPs executed: {len(self.results['prps_executed'])}")
        print(f"PRPs passed: {len(self.results['prps_passed'])}")
        print(f"PRPs failed: {len(self.results['prps_failed'])}")

        if self.results["prps_passed"]:
            print(f"\nPASSED PRPs: {', '.join(self.results['prps_passed'])}")

        if self.results["prps_failed"]:
            print(f"\nFAILED PRPs: {', '.join(self.results['prps_failed'])}")

        print(f"\nOVERALL RESULT: {'SUCCESS' if self.results['overall_success'] else 'FAILURE'}")

        # Show individual PRP details
        print("\nDetailed Results:")
        for execution in self.results["prps_executed"]:
            status = "PASS" if execution["success"] else "FAIL"
            time_taken = execution.get("execution_time", 0)
            print(f"  PRP-{execution['prp_id']}: {status} ({time_taken:.1f}s) - {execution['prp_name']}")

        # Save complete results
        with open("execute_all_fixes_results.json", "w") as f:
            json.dump(self.results, f, indent=2)

        print(f"\nComplete results saved to: execute_all_fixes_results.json")

    def execute(self) -> bool:
        """Main execution method"""
        print("Version MVP2 Fixup PRP Master Execution")
        print("=" * 80)

        # Check prerequisites
        if not self.check_prerequisites():
            print("ABORTING: Prerequisites not met")
            return False

        # Execute all PRPs
        success = self.execute_all_prps()

        # Print summary
        self.print_final_summary()

        return success

def main():
    """Main entry point"""
    executor = FixupMasterExecution()
    success = executor.execute()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
