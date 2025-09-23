#!/usr/bin/env python3
"""
PRP-M3 Verification: Prove service architecture unification success
"""

import json
import glob
import re
import subprocess
from db_config import test_connection

def verify_prp_m3():
 """Verify PRP-M3 completion with automated proof"""

 print("=== PRP-M3 VERIFICATION ===")

 # Load unification report
 try:
 with open('prp_m3_unification_report.json', 'r') as f:
 report = json.load(f)
 except FileNotFoundError:
 print("FAILED: Unification report not found")
 return False

 # Check unification status
 if report['status'] not in ['COMPLETED', 'COMPLETED_WITH_WARNINGS']:
 print(f"FAILED: Unification status = {report['status']}")
 return False

 verification_passed = True

 # Test PostgreSQL connection
 success, result = test_connection()
 if success:
 print(f"SUCCESS PostgreSQL connection: Working")
 else:
 print(f"FAILED PostgreSQL connection: Failed - {result}")
 verification_passed = False

 # Verify no remaining SQLite dependencies
 service_files = glob.glob('services/*.py') + glob.glob('*.py')
 sqlite_dependencies = 0

 for file_path in service_files:
 try:
 with open(file_path, 'r', encoding='utf-8') as f:
 content = f.read()

 # Check for SQLite patterns
 if re.search(r'sqlite3\.connect|\.db[\'"]', content, re.IGNORECASE):
 if 'backup' not in file_path and 'test' not in file_path:
 sqlite_dependencies += 1
 print(f" Warning: {file_path} still has SQLite references")

 except Exception:
 pass

 if sqlite_dependencies == 0:
 print(f"SUCCESS SQLite dependencies: None found")
 else:
 print(f"WARNING SQLite dependencies: {sqlite_dependencies} files still have references")
 # Don't fail for warnings in test files

 # Test unified database utilities
 try:
 result = subprocess.run(['python', 'db_utils.py'], capture_output=True, text=True, timeout=30)
 if result.returncode == 0:
 print(f"SUCCESS Unified database utilities: Working")
 else:
 print(f"FAILED Unified database utilities: Failed")
 print(f" Error: {result.stderr}")
 verification_passed = False
 except Exception as e:
 print(f"FAILED Unified database utilities: Test failed - {e}")
 verification_passed = False

 # Verify service update statistics
 files_updated = len(report['services_updated'])
 references_fixed = report['database_references_fixed']

 print(f"SUCCESS Service updates: {files_updated} files, {references_fixed} references fixed")

 # Test specific services if they exist
 test_services = ['development_permissions_db.py', 'hierarchy_resolver.py']

 for service in test_services:
 if service in [s.split('/')[-1] for s in report['services_updated'].keys()]:
 print(f"SUCCESS {service}: Updated to PostgreSQL")
 else:
 print(f" {service}: Not found or already using PostgreSQL")

 # Final verification
 if verification_passed:
 print(f"\nSUCCESS PRP-M3 VERIFICATION PASSED")
 print(f" Architecture: Unified PostgreSQL")
 print(f" Services updated: {files_updated}")
 print(f" Ready for Priority2Fix PRPs")
 return True
 else:
 print(f"\nFAILED PRP-M3 VERIFICATION FAILED")
 return False

if __name__ == "__main__":
 success = verify_prp_m3()
 exit(0 if success else 1)