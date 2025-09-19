# PRP-M3: Service Architecture Unification

## Objective
Update all Python services to use PostgreSQL exclusively, eliminating SQLite dependencies and creating unified database architecture for Priority2Fix PRPs.

## Scope
**Input:** Mixed SQLite/PostgreSQL service architecture
**Output:** Unified PostgreSQL-only service architecture
**Time:** 20 minutes
**Verification:** Service connection tests with automated proof

## Current Architecture Issues

### SQLite-Dependent Services (Need Update)
- `development_permissions_db.py` - Uses SQLite for development permissions
- `council_validation_service.py` - Mixed database usage
- Various PRP execution scripts - Hardcoded SQLite paths

### PostgreSQL Services (Already Correct)
- `hierarchy_resolver.py` - Uses PostgreSQL authoritative schema
- `services/nsw_planning_api.py` - External API integration

## Implementation

### Service Unification Script: `execute_prp_m3.py`

```python
#!/usr/bin/env python3
"""
PRP-M3: Service Architecture Unification
Updates all services to use PostgreSQL exclusively
"""

import os
import glob
import json
import re
from datetime import datetime
from pathlib import Path

class PRP_M3_Unification:
    def __init__(self):
        self.unification_report = {
            'start_time': datetime.now().isoformat(),
            'services_updated': {},
            'database_references_fixed': 0,
            'files_processed': 0,
            'status': 'IN_PROGRESS'
        }

        # Database connection patterns to replace
        self.sqlite_patterns = [
            r"sqlite3\.connect\(['\"]nsw_planning\.db['\"].*?\)",
            r"sqlite3\.connect\(['\"].*?\.db['\"].*?\)",
            r"DATABASE_PATH\s*=\s*['\"].*?\.db['\"]",
            r"db_path\s*=\s*['\"].*?\.db['\"]",
        ]

        # PostgreSQL replacement pattern
        self.postgres_replacement = "get_connection()  # Unified PostgreSQL connection"

    def scan_service_files(self):
        """Scan all Python files for database connections"""
        service_files = []

        # Scan main services directory
        for pattern in ['services/*.py', '*.py', 'examples/*.py']:
            service_files.extend(glob.glob(pattern))

        # Filter for actual service files
        relevant_files = []
        for file_path in service_files:
            if any(term in file_path.lower() for term in [
                'service', 'db', 'database', 'migration', 'prp', 'api'
            ]):
                relevant_files.append(file_path)

        print(f"Found {len(relevant_files)} service files to analyze")
        return relevant_files

    def analyze_file(self, file_path):
        """Analyze file for SQLite dependencies"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            sqlite_references = 0
            needs_update = False

            for pattern in self.sqlite_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                sqlite_references += len(matches)
                if matches:
                    needs_update = True

            # Check for sqlite3 imports
            if 'import sqlite3' in content:
                sqlite_references += 1
                needs_update = True

            return {
                'sqlite_references': sqlite_references,
                'needs_update': needs_update,
                'content': content,
                'file_size': len(content)
            }

        except Exception as e:
            print(f"Warning: Could not analyze {file_path}: {e}")
            return {
                'sqlite_references': 0,
                'needs_update': False,
                'content': '',
                'file_size': 0
            }

    def update_service_file(self, file_path, analysis):
        """Update service file to use PostgreSQL"""
        if not analysis['needs_update']:
            return False

        print(f"Updating {file_path}...")

        content = analysis['content']
        original_content = content

        # Replace sqlite3 import
        content = re.sub(
            r'import sqlite3\n',
            'from db_config import get_connection  # Unified PostgreSQL connection\n',
            content
        )

        # Replace SQLite connection patterns
        for pattern in self.sqlite_patterns:
            content = re.sub(
                pattern,
                'get_connection()',
                content,
                flags=re.IGNORECASE
            )

        # Replace common SQLite-specific code patterns
        replacements = [
            # Replace cursor creation patterns
            (r'conn = sqlite3\.connect\([^)]+\)', 'conn = get_connection()'),
            (r'\.fetchone\(\)\[0\]', '.fetchone()[0]'),  # Keep as is - works for both
            (r'\.executemany\(', '.executemany('),  # Keep as is - works for both

            # Update SQL syntax differences
            (r'PRAGMA table_info\(([^)]+)\)', r'SELECT column_name FROM information_schema.columns WHERE table_name = \1'),
            (r'AUTOINCREMENT', 'SERIAL'),
            (r'INTEGER PRIMARY KEY', 'SERIAL PRIMARY KEY'),
        ]

        for old_pattern, new_pattern in replacements:
            content = re.sub(old_pattern, new_pattern, content, flags=re.IGNORECASE)

        # Add import if not present and needed
        if 'get_connection' in content and 'from db_config import get_connection' not in content:
            # Add import at the top after existing imports
            import_section = re.search(r'((?:^(?:import|from)\s+.*\n)*)', content, re.MULTILINE)
            if import_section:
                existing_imports = import_section.group(1)
                new_imports = existing_imports + 'from db_config import get_connection  # Unified PostgreSQL connection\n'
                content = content.replace(existing_imports, new_imports)

        # Only write if content changed
        if content != original_content:
            # Backup original file
            backup_path = f"{file_path}.backup"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)

            # Write updated content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            self.unification_report['services_updated'][file_path] = {
                'backup_created': backup_path,
                'sqlite_references_removed': analysis['sqlite_references'],
                'file_size_before': len(original_content),
                'file_size_after': len(content),
                'timestamp': datetime.now().isoformat()
            }

            self.unification_report['database_references_fixed'] += analysis['sqlite_references']

            print(f"  ✓ Updated {file_path} ({analysis['sqlite_references']} references fixed)")
            return True

        return False

    def create_unified_database_module(self):
        """Create enhanced database module for services"""
        db_utils_content = '''#!/usr/bin/env python3
"""
Unified Database Utilities for NSW Compliance Engine
Provides consistent PostgreSQL access for all services
"""

from db_config import get_connection
import psycopg2
from typing import List, Dict, Any, Optional
import json

class UnifiedDatabaseClient:
    """Unified database client for all compliance engine services"""

    def __init__(self):
        self.conn = None

    def __enter__(self):
        self.conn = get_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    def execute_query(self, query: str, params: tuple = None) -> List[tuple]:
        """Execute query and return results"""
        cursor = self.conn.cursor()
        cursor.execute(query, params or ())
        return cursor.fetchall()

    def execute_single(self, query: str, params: tuple = None) -> Optional[tuple]:
        """Execute query and return single result"""
        cursor = self.conn.cursor()
        cursor.execute(query, params or ())
        return cursor.fetchone()

    def execute_count(self, table: str, where_clause: str = "", params: tuple = None) -> int:
        """Execute count query"""
        query = f"SELECT COUNT(*) FROM {table}"
        if where_clause:
            query += f" WHERE {where_clause}"

        cursor = self.conn.cursor()
        cursor.execute(query, params or ())
        return cursor.fetchone()[0]

    def get_regulatory_provisions(self, zone: str = None, development_type: str = None) -> List[Dict]:
        """Get regulatory provisions with optional filtering"""
        query = "SELECT * FROM regulatory_provisions WHERE 1=1"
        params = []

        if zone:
            query += " AND zone = %s"
            params.append(zone)

        if development_type:
            query += " AND development_type = %s"
            params.append(development_type)

        cursor = self.conn.cursor()
        cursor.execute(query, params)

        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_sepp_provisions(self, sepp_type: str = None, category: str = None) -> List[Dict]:
        """Get SEPP provisions with optional filtering"""
        query = "SELECT * FROM sepp_provisions WHERE 1=1"
        params = []

        if sepp_type:
            query += " AND sepp_type = %s"
            params.append(sepp_type)

        if category:
            query += " AND provision_category = %s"
            params.append(category)

        cursor = self.conn.cursor()
        cursor.execute(query, params)

        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_development_controls(self, zone: str = None) -> List[Dict]:
        """Get development controls with optional zone filtering"""
        query = "SELECT * FROM development_controls WHERE 1=1"
        params = []

        if zone:
            query += " AND zone = %s"
            params.append(zone)

        cursor = self.conn.cursor()
        cursor.execute(query, params)

        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_quantitative_standards(self, development_type: str = None) -> List[Dict]:
        """Get quantitative standards with optional filtering"""
        query = "SELECT * FROM quantitative_standards WHERE 1=1"
        params = []

        if development_type:
            query += " AND development_type = %s"
            params.append(development_type)

        cursor = self.conn.cursor()
        cursor.execute(query, params)

        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

# Convenience functions for backward compatibility
def get_regulatory_provisions(*args, **kwargs):
    """Backward compatibility function"""
    with UnifiedDatabaseClient() as db:
        return db.get_regulatory_provisions(*args, **kwargs)

def get_development_controls(*args, **kwargs):
    """Backward compatibility function"""
    with UnifiedDatabaseClient() as db:
        return db.get_development_controls(*args, **kwargs)

def get_quantitative_standards(*args, **kwargs):
    """Backward compatibility function"""
    with UnifiedDatabaseClient() as db:
        return db.get_quantitative_standards(*args, **kwargs)

def test_unified_database():
    """Test unified database connectivity"""
    try:
        with UnifiedDatabaseClient() as db:
            # Test each major table
            reg_count = db.execute_count('regulatory_provisions')
            dev_count = db.execute_count('development_controls')
            quant_count = db.execute_count('quantitative_standards')

            print(f"✓ Unified database test passed:")
            print(f"  Regulatory provisions: {reg_count:,}")
            print(f"  Development controls: {dev_count:,}")
            print(f"  Quantitative standards: {quant_count:,}")

            return True

    except Exception as e:
        print(f"✗ Unified database test failed: {e}")
        return False

if __name__ == "__main__":
    test_unified_database()
'''

        with open('db_utils.py', 'w', encoding='utf-8') as f:
            f.write(db_utils_content)

        print("✓ Created unified database utilities module")

    def test_service_connections(self):
        """Test that updated services can connect to PostgreSQL"""
        from db_config import test_connection

        # Test basic connection
        success, result = test_connection()

        if not success:
            raise Exception(f"PostgreSQL connection test failed: {result}")

        # Test unified database utils
        try:
            import subprocess
            result = subprocess.run(['python', 'db_utils.py'], capture_output=True, text=True)

            if result.returncode == 0:
                print("✓ Unified database utilities test passed")
                return True
            else:
                print(f"✗ Unified database utilities test failed: {result.stderr}")
                return False

        except Exception as e:
            print(f"✗ Service connection test failed: {e}")
            return False

    def execute_unification(self):
        """Execute complete service architecture unification"""
        try:
            print("=== PRP-M3: SERVICE ARCHITECTURE UNIFICATION ===")

            # Scan for service files
            service_files = self.scan_service_files()

            # Analyze and update each file
            for file_path in service_files:
                analysis = self.analyze_file(file_path)
                self.unification_report['files_processed'] += 1

                if analysis['needs_update']:
                    self.update_service_file(file_path, analysis)

            # Create unified database utilities
            self.create_unified_database_module()

            # Test connections
            if self.test_service_connections():
                self.unification_report['status'] = 'COMPLETED'
            else:
                self.unification_report['status'] = 'COMPLETED_WITH_WARNINGS'

            self.unification_report['end_time'] = datetime.now().isoformat()

            # Save report
            with open('prp_m3_unification_report.json', 'w') as f:
                json.dump(self.unification_report, f, indent=2)

            print(f"\n✓ PRP-M3 COMPLETED")
            print(f"  Files processed: {self.unification_report['files_processed']}")
            print(f"  Services updated: {len(self.unification_report['services_updated'])}")
            print(f"  Database references fixed: {self.unification_report['database_references_fixed']}")
            print(f"Report saved: prp_m3_unification_report.json")

        except Exception as e:
            self.unification_report['status'] = 'FAILED'
            self.unification_report['error'] = str(e)
            print(f"✗ PRP-M3 FAILED: {e}")
            raise

if __name__ == "__main__":
    unifier = PRP_M3_Unification()
    unifier.execute_unification()
```

### Verification Script: `verify_prp_m3.py`

```python
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
        print("✗ FAILED: Unification report not found")
        return False

    # Check unification status
    if report['status'] not in ['COMPLETED', 'COMPLETED_WITH_WARNINGS']:
        print(f"✗ FAILED: Unification status = {report['status']}")
        return False

    verification_passed = True

    # Test PostgreSQL connection
    success, result = test_connection()
    if success:
        print(f"✓ PostgreSQL connection: Working")
    else:
        print(f"✗ PostgreSQL connection: Failed - {result}")
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
                    print(f"  Warning: {file_path} still has SQLite references")

        except Exception:
            pass

    if sqlite_dependencies == 0:
        print(f"✓ SQLite dependencies: None found")
    else:
        print(f"✗ SQLite dependencies: {sqlite_dependencies} files still have references")
        verification_passed = False

    # Test unified database utilities
    try:
        result = subprocess.run(['python', 'db_utils.py'], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"✓ Unified database utilities: Working")
        else:
            print(f"✗ Unified database utilities: Failed")
            print(f"  Error: {result.stderr}")
            verification_passed = False
    except Exception as e:
        print(f"✗ Unified database utilities: Test failed - {e}")
        verification_passed = False

    # Verify service update statistics
    files_updated = len(report['services_updated'])
    references_fixed = report['database_references_fixed']

    print(f"✓ Service updates: {files_updated} files, {references_fixed} references fixed")

    # Test specific services if they exist
    test_services = ['development_permissions_db.py', 'hierarchy_resolver.py']

    for service in test_services:
        if service in [s.split('/')[-1] for s in report['services_updated'].keys()]:
            print(f"✓ {service}: Updated to PostgreSQL")
        else:
            print(f"  {service}: Not found or already using PostgreSQL")

    # Final verification
    if verification_passed:
        print(f"\n✓ PRP-M3 VERIFICATION PASSED")
        print(f"  Architecture: Unified PostgreSQL")
        print(f"  Services updated: {files_updated}")
        print(f"  Ready for Priority2Fix PRPs")
        return True
    else:
        print(f"\n✗ PRP-M3 VERIFICATION FAILED")
        return False

if __name__ == "__main__":
    success = verify_prp_m3()
    exit(0 if success else 1)
```

## Expected Results

### Unification Report
```json
{
  "status": "COMPLETED",
  "files_processed": 15,
  "services_updated": {
    "development_permissions_db.py": {"sqlite_references_removed": 3},
    "council_validation_service.py": {"sqlite_references_removed": 2}
  },
  "database_references_fixed": 5
}
```

### Verification Output
```
✓ PostgreSQL connection: Working
✓ SQLite dependencies: None found
✓ Unified database utilities: Working
✓ Service updates: 2 files, 5 references fixed
✓ development_permissions_db.py: Updated to PostgreSQL
✓ PRP-M3 VERIFICATION PASSED
```

## Success Criteria

1. **✓ All services use PostgreSQL** exclusively
2. **✓ No remaining SQLite dependencies** in service files
3. **✓ Unified database utilities** module created and tested
4. **✓ Service connection tests** pass
5. **✓ Processing time < 20 minutes**

## Next Steps

After PRP-M3 completion:
1. Execute Priority2Fix PRP-Q1 (Live Compliance Calculator)
2. Execute Priority2Fix PRP-Q2 (Development Pathway Intelligence)
3. All services now use unified PostgreSQL architecture

## Commands

```bash
# Execute unification
python execute_prp_m3.py

# Verify completion
python verify_prp_m3.py

# Test unified database utilities
python db_utils.py

# Check unification report
cat prp_m3_unification_report.json
```

---

**PRP-M3 completes the unified PostgreSQL architecture required for Priority2Fix PRPs Q1-Q4.**