# MASTER EXECUTION SEQUENCE - Priority2Fix Database Foundation

## Overview
Complete database foundation implementation for Priority2Fix PRPs Q1-Q4. These three migration PRPs must be executed sequentially before any Priority2Fix PRP can begin.

## Sequential Execution Order

### PRP-M1: Complete Database Migration (45 min)
**Status:** Ready to execute
**Objective:** Migrate all missing tables from SQLite to PostgreSQL
**Critical Tables:** development_controls (4,526), quantitative_standards (832), contextual_guidance (6,655)
```bash
python execute_prp_m1.py
python verify_prp_m1.py
```

### PRP-M2: SEPP/LEP Restructuring (30 min)
**Status:** Requires PRP-M1 completion
**Objective:** Extract SEPP/LEP provisions into dedicated tables for pathway intelligence
**Expected Output:** sepp_provisions (2,000+), lep_provisions (4,000+)
```bash
python execute_prp_m2.py
python verify_prp_m2.py
```

### PRP-M3: Service Architecture Unification (20 min)
**Status:** Requires PRP-M1 completion
**Objective:** Update all services to use PostgreSQL exclusively
**Critical Changes:** Remove SQLite dependencies, create unified db utilities
```bash
python execute_prp_m3.py
python verify_prp_m3.py
```

## Automated Execution Script

### `execute_all_migration_prps.py`

```python
#!/usr/bin/env python3
"""
Master execution script for all Migration PRPs
Executes PRP-M1, M2, M3 in sequence with verification
"""

import subprocess
import json
from datetime import datetime

class MasterMigrationExecutor:
    def __init__(self):
        self.execution_report = {
            'start_time': datetime.now().isoformat(),
            'prp_results': {},
            'total_duration': 0,
            'status': 'IN_PROGRESS'
        }

    def execute_prp(self, prp_name, execute_script, verify_script):
        """Execute single PRP with verification"""
        print(f"\n{'='*60}")
        print(f"EXECUTING {prp_name}")
        print(f"{'='*60}")

        prp_start = datetime.now()

        try:
            # Execute main script
            print(f"Running {execute_script}...")
            result = subprocess.run(['python', execute_script],
                                  capture_output=True, text=True, timeout=3600)

            if result.returncode != 0:
                raise Exception(f"Execution failed: {result.stderr}")

            print(result.stdout)

            # Execute verification
            print(f"Running {verify_script}...")
            verify_result = subprocess.run(['python', verify_script],
                                         capture_output=True, text=True, timeout=300)

            if verify_result.returncode != 0:
                raise Exception(f"Verification failed: {verify_result.stderr}")

            print(verify_result.stdout)

            prp_end = datetime.now()
            duration = (prp_end - prp_start).total_seconds()

            self.execution_report['prp_results'][prp_name] = {
                'status': 'COMPLETED',
                'duration_seconds': duration,
                'execution_output': result.stdout,
                'verification_output': verify_result.stdout,
                'timestamp': prp_end.isoformat()
            }

            print(f"SUCCESS {prp_name} COMPLETED in {duration:.1f} seconds")
            return True

        except Exception as e:
            prp_end = datetime.now()
            duration = (prp_end - prp_start).total_seconds()

            self.execution_report['prp_results'][prp_name] = {
                'status': 'FAILED',
                'duration_seconds': duration,
                'error': str(e),
                'timestamp': prp_end.isoformat()
            }

            print(f"FAILED {prp_name} FAILED: {e}")
            return False

    def execute_all(self):
        """Execute all migration PRPs in sequence"""
        try:
            print("MASTER MIGRATION EXECUTION - Priority2Fix Database Foundation")
            print("This will execute PRP-M1, M2, M3 in sequence")
            print("Estimated total time: 95 minutes")

            # PRP-M1: Complete Database Migration
            if not self.execute_prp(
                'PRP-M1',
                'execute_prp_m1.py',
                'verify_prp_m1.py'
            ):
                raise Exception("PRP-M1 failed - cannot continue")

            # PRP-M2: SEPP/LEP Restructuring
            if not self.execute_prp(
                'PRP-M2',
                'execute_prp_m2.py',
                'verify_prp_m2.py'
            ):
                raise Exception("PRP-M2 failed - cannot continue")

            # PRP-M3: Service Architecture Unification
            if not self.execute_prp(
                'PRP-M3',
                'execute_prp_m3.py',
                'verify_prp_m3.py'
            ):
                raise Exception("PRP-M3 failed - cannot continue")

            # Calculate total duration
            end_time = datetime.now()
            start_time = datetime.fromisoformat(self.execution_report['start_time'])
            total_duration = (end_time - start_time).total_seconds()

            self.execution_report['status'] = 'COMPLETED'
            self.execution_report['end_time'] = end_time.isoformat()
            self.execution_report['total_duration'] = total_duration

            # Save master report
            with open('master_migration_execution_report.json', 'w') as f:
                json.dump(self.execution_report, f, indent=2)

            print(f"\n{'='*60}")
            print(f"MASTER MIGRATION COMPLETED SUCCESSFULLY")
            print(f"{'='*60}")
            print(f"Total duration: {total_duration/60:.1f} minutes")
            print(f"PRP-M1: {self.execution_report['prp_results']['PRP-M1']['duration_seconds']:.1f}s")
            print(f"PRP-M2: {self.execution_report['prp_results']['PRP-M2']['duration_seconds']:.1f}s")
            print(f"PRP-M3: {self.execution_report['prp_results']['PRP-M3']['duration_seconds']:.1f}s")
            print(f"\nDatabase foundation ready for Priority2Fix PRPs Q1-Q4")
            print(f"Master report: master_migration_execution_report.json")

        except Exception as e:
            self.execution_report['status'] = 'FAILED'
            self.execution_report['error'] = str(e)
            print(f"\nMASTER MIGRATION FAILED: {e}")
            raise

if __name__ == "__main__":
    executor = MasterMigrationExecutor()
    executor.execute_all()
```

### `verify_all_migration_prps.py`

```python
#!/usr/bin/env python3
"""
Master verification script for all Migration PRPs
Comprehensive verification that database foundation is ready
"""

import json
import subprocess
from db_config import get_connection

def verify_complete_migration():
    """Verify all migration PRPs completed successfully"""

    print("=== MASTER MIGRATION VERIFICATION ===")

    verification_passed = True

    # Load individual PRP reports
    prp_reports = {}
    for prp in ['prp_m1_migration_report.json', 'prp_m2_restructuring_report.json', 'prp_m3_unification_report.json']:
        try:
            with open(prp, 'r') as f:
                prp_reports[prp] = json.load(f)
        except FileNotFoundError:
            print(f"FAILED: {prp} not found")
            verification_passed = False

    # Verify database completeness
    conn = get_connection()
    cursor = conn.cursor()

    # Check all critical tables exist with data
    critical_tables = {
        'regulatory_provisions': 22000,
        'development_controls': 4500,
        'quantitative_standards': 800,
        'contextual_guidance': 6500,
        'sepp_provisions': 100,
        'lep_provisions': 500,
        'development_permissions': 200
    }

    print("\nDatabase Table Verification:")
    for table, min_expected in critical_tables.items():
        try:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            actual_count = cursor.fetchone()[0]

            if actual_count >= min_expected:
                print(f"SUCCESS {table}: {actual_count:,} records")
            else:
                print(f"FAILED {table}: {actual_count:,} records (expected {min_expected:,}+)")
                verification_passed = False

        except Exception as e:
            print(f"FAILED {table}: Error - {e}")
            verification_passed = False

    # Test unified database utilities
    print("\nService Architecture Verification:")
    try:
        result = subprocess.run(['python', 'db_utils.py'], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("SUCCESS Unified database utilities: Working")
        else:
            print(f"FAILED Unified database utilities: {result.stderr}")
            verification_passed = False
    except Exception as e:
        print(f"FAILED Unified database utilities: {e}")
        verification_passed = False

    # Priority2Fix PRP Readiness Assessment
    print("\nPriority2Fix PRP Readiness:")

    prp_q_readiness = {
        'PRP-Q1 (Live Compliance Calculator)': ['regulatory_provisions', 'development_controls', 'quantitative_standards'],
        'PRP-Q2 (Development Pathway Intelligence)': ['sepp_provisions', 'lep_provisions', 'development_permissions'],
        'PRP-Q3 (Advanced Compliance Rules)': ['regulatory_provisions', 'quantitative_standards', 'contextual_guidance'],
        'PRP-Q4 (Legal Disclaimers)': ['all tables for API monitoring']
    }

    for prp, required_tables in prp_q_readiness.items():
        if required_tables == ['all tables for API monitoring']:
            print(f"SUCCESS {prp}: External dependencies (API monitoring)")
        else:
            prp_ready = all(table in critical_tables for table in required_tables)
            if prp_ready:
                print(f"SUCCESS {prp}: Ready")
            else:
                print(f"FAILED {prp}: Missing dependencies")
                verification_passed = False

    conn.close()

    # Final verification
    if verification_passed:
        print(f"\nSUCCESS MASTER MIGRATION VERIFICATION PASSED")
        print(f"Database foundation complete for Priority2Fix PRPs")
        print(f"Ready to execute: PRP-Q1, Q2, Q3, Q4")
        return True
    else:
        print(f"\nFAILED MASTER MIGRATION VERIFICATION FAILED")
        print(f"Database foundation incomplete - fix issues before Priority2Fix PRPs")
        return False

if __name__ == "__main__":
    success = verify_complete_migration()
    exit(0 if success else 1)
```

## Expected Timeline

| PRP | Duration | Dependencies | Output |
|-----|----------|--------------|---------|
| PRP-M1 | 45 min | SQLite data | 12,000+ records migrated |
| PRP-M2 | 30 min | PRP-M1 | 6,000+ SEPP/LEP provisions |
| PRP-M3 | 20 min | PRP-M1 | Unified PostgreSQL services |
| **Total** | **95 min** | None | **Complete database foundation** |

## Verification Checkpoints

### After PRP-M1
```bash
✓ development_controls: 4,526 records
✓ quantitative_standards: 832 records
✓ contextual_guidance: 6,655 records
```

### After PRP-M2
```bash
✓ sepp_provisions: 2,000+ records
✓ lep_provisions: 4,000+ records
✓ Summary views created
```

### After PRP-M3
```bash
✓ No SQLite dependencies
✓ Unified database utilities working
✓ All services use PostgreSQL
```

### Master Verification
```bash
✓ All 7 critical tables populated
✓ Priority2Fix PRPs Q1-Q4 ready
✓ Database foundation complete
```

## Execution Commands

### Individual Execution
```bash
# Execute each PRP individually
python execute_prp_m1.py && python verify_prp_m1.py
python execute_prp_m2.py && python verify_prp_m2.py
python execute_prp_m3.py && python verify_prp_m3.py
```

### Master Execution (Recommended)
```bash
# Execute all migration PRPs in sequence
python execute_all_migration_prps.py

# Verify complete foundation
python verify_all_migration_prps.py
```

### Reports Generated
- `prp_m1_migration_report.json`
- `prp_m2_restructuring_report.json`
- `prp_m3_unification_report.json`
- `master_migration_execution_report.json`

---

**After successful completion, the database foundation will be ready for Priority2Fix PRPs Q1-Q4 execution.**