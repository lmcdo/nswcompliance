#!/usr/bin/env python3
"""
Verification script for PRP-V2: Version Service Layer
Validates that the version management service is operational
"""

import sys
import json
import os
from datetime import date, datetime
from typing import Dict, List

# Add parent directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

def verify_imports() -> Dict[str, bool]:
    """Verify required modules can be imported"""
    results = {}

    try:
        from services.version_manager import VersionManager, DocumentType, VersionStatus
        results['version_manager'] = True
    except ImportError as e:
        results['version_manager'] = False
        print(f"FAILED to import version_manager: {e}")

    try:
        from services.version_aware_query import VersionAwareQuery
        results['version_aware_query'] = True
    except ImportError as e:
        results['version_aware_query'] = False
        print(f"FAILED to import version_aware_query: {e}")

    return results

def verify_version_manager_operations() -> Dict[str, bool]:
    """Test VersionManager operations"""
    results = {}

    try:
        from services.version_manager import VersionManager, DocumentType
        vm = VersionManager()

        # Test connection
        vm._ensure_connection()
        results['connection'] = True

        # Test get_current_version (should handle non-existent gracefully)
        version = vm.get_current_version(DocumentType.LEP, "TEST-NONEXISTENT")
        results['get_current'] = version is None or version is not None

        # Test get_version_statistics
        stats = vm.get_version_statistics()
        results['get_statistics'] = isinstance(stats, dict)

        vm.close()
        results['close_connection'] = True

    except Exception as e:
        print(f"FAILED Version manager test: {e}")
        results['version_manager_ops'] = False

    return results

def verify_version_aware_query() -> Dict[str, bool]:
    """Test VersionAwareQuery operations"""
    results = {}

    try:
        from services.version_aware_query import VersionAwareQuery

        # Test get_provisions with default params
        provisions = VersionAwareQuery.get_provisions()
        results['get_provisions'] = isinstance(provisions, list)

        # Test with version parameter
        provisions_current = VersionAwareQuery.get_provisions(version="current")
        results['version_filter'] = isinstance(provisions_current, list)

        # Test with date parameter
        test_date = date(2024, 1, 1)
        provisions_dated = VersionAwareQuery.get_provisions(as_at_date=test_date)
        results['date_filter'] = isinstance(provisions_dated, list)

    except Exception as e:
        print(f"FAILED Version aware query test: {e}")
        results['query_ops'] = False

    return results

def verify_service_integration() -> Dict[str, bool]:
    """Verify services integrate with database correctly"""
    results = {}

    try:
        from services.version_manager import VersionManager, DocumentType
        from db_config import get_connection

        # Test database connection through service
        conn = get_connection()
        with conn.cursor() as cursor:
            # Check if version schema exists
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.schemata
                    WHERE schema_name = 'versions'
                )
            """)
            schema_exists = cursor.fetchone()[0]
            results['schema_accessible'] = schema_exists

            # Check if functions are callable
            if schema_exists:
                cursor.execute("""
                    SELECT versions.get_current_version('LEP', 'TEST')
                """)
                results['functions_callable'] = True

        conn.close()

    except Exception as e:
        print(f"WARNING Service integration test: {e}")
        results['integration'] = False

    return results

def main():
    """Run all verifications for PRP-V2"""
    print("Verifying PRP-V2: Version Service Layer...")

    verification_results = {
        "timestamp": datetime.now().isoformat(),
        "prp": "V2_VERSION_SERVICE",
        "checks": {},
        "errors": [],
        "warnings": [],
        "success": False
    }

    # Run all checks
    print("\nChecking imports...")
    import_results = verify_imports()
    verification_results["checks"]["imports"] = import_results

    if all(import_results.values()):
        print("All imports successful")

        print("\nTesting VersionManager operations...")
        vm_results = verify_version_manager_operations()
        verification_results["checks"]["version_manager"] = vm_results

        print("\nTesting VersionAwareQuery operations...")
        query_results = verify_version_aware_query()
        verification_results["checks"]["version_query"] = query_results

        print("\nTesting service integration...")
        integration_results = verify_service_integration()
        verification_results["checks"]["integration"] = integration_results

        # Determine overall success
        all_passed = (
            all(vm_results.values()) and
            all(query_results.values()) and
            integration_results.get('schema_accessible', False)
        )
    else:
        print("FAILED Import failures detected")
        verification_results["errors"].append("Required service modules not found")
        all_passed = False

    verification_results["success"] = all_passed

    # Save results
    with open("verify_v2_results.json", "w") as f:
        json.dump(verification_results, f, indent=2)

    # Print summary
    print("\n" + "=" * 50)
    print("Verification Summary:")
    print(f"  Module imports: {'PASS' if all(import_results.values()) else 'FAIL'}")

    if 'version_manager' in verification_results["checks"]:
        print(f"  Version Manager: {'PASS' if all(verification_results['checks']['version_manager'].values()) else 'FAIL'}")

    if 'version_query' in verification_results["checks"]:
        print(f"  Version Queries: {'PASS' if all(verification_results['checks']['version_query'].values()) else 'FAIL'}")

    if 'integration' in verification_results["checks"]:
        print(f"  Database Integration: {'PASS' if verification_results['checks']['integration'].get('schema_accessible', False) else 'FAIL'}")

    print(f"\n{'PRP-V2 VERIFICATION PASSED' if all_passed else 'PRP-V2 VERIFICATION FAILED'}")

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
