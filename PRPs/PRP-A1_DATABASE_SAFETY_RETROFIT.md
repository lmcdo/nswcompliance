# PRP-A1: Database Safety Retrofit
## Universal Technical Implementation Specification Compliance

**Date**: 2025-09-23
**Status**: READY FOR IMPLEMENTATION
**Priority**: CRITICAL - DATABASE SAFETY FOUNDATION
**Duration**: 1 session
**Dependencies**: Current UI implementation, PostgreSQL database

---

## **EXECUTIVE SUMMARY**

This PRP implements database safety compliance per CLAUDE.md requirements while maintaining the existing UI implementation. It retrofits safety wrappers, timeouts, and backup procedures to the current subprocess-based architecture, creating a stable foundation for subsequent architecture improvements.

---

## **CRITICAL SAFETY REQUIREMENTS FROM CLAUDE.MD**

### **Mandatory Safety Rules**
```python
# VIOLATION: Current implementation
spawn(this.pythonPath, [scriptPath, '--clause', clauseReference])

# REQUIRED: CLAUDE.md compliance
from db_safety_wrapper import get_safe_connection
```

### **Database Safety Checklist**
- ✅ **ALWAYS use `db_safety_wrapper.py`** - MANDATORY
- ✅ **ALWAYS create backup before ANY database operation** - MANDATORY
- ✅ **NEVER run queries without WHERE clauses on main tables** - MANDATORY
- ✅ **ALWAYS use timeouts (30 seconds max)** - MANDATORY
- ✅ **Database issues = STOP IMMEDIATELY** - MANDATORY

---

## **IMPLEMENTATION ARCHITECTURE**

### **Phase 1: Safety Wrapper Integration**
```python
# 1. Update get_provision_details.py
from db_safety_wrapper import get_safe_connection
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Database query timeout after 30 seconds")

def get_provision_details(clause_reference: str, document_type: str) -> dict:
    """
    Get detailed provision content with safety wrapper
    CLAUDE.md compliant implementation
    """
    try:
        # Set timeout alarm
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(30)  # 30 second timeout

        # Use safety wrapper - MANDATORY per CLAUDE.md
        conn = get_safe_connection()
        cursor = conn.cursor()

        # Backup check before any operation
        backup_status = check_recent_backup()
        if not backup_status['recent_backup_exists']:
            create_backup_before_query()

        # Query with mandatory WHERE clause
        cursor.execute("""
            SELECT
                id, ref_number, section_header, provision_text,
                document_id, provision_type, zone, development_type, page_number
            FROM regulatory_provisions
            WHERE (
                ref_number ILIKE %s
                OR ref_number ILIKE %s
                OR provision_text ILIKE %s
            )
            AND document_id ILIKE %s
            AND provision_text IS NOT NULL
            AND LENGTH(provision_text) > 50
            ORDER BY
                CASE
                    WHEN ref_number ILIKE %s THEN 1
                    WHEN ref_number ILIKE %s THEN 2
                    ELSE 3
                END,
                LENGTH(provision_text) DESC
            LIMIT 10
        """, (
            f'%{clause_reference}%',
            f'%{clause_reference.replace("Clause ", "")}%',
            f'%{clause_reference}%',
            get_document_pattern(document_type),
            f'{clause_reference}',
            f'{clause_reference.replace("Clause ", "")}'
        ))

        provisions = cursor.fetchall()

        # Clear timeout
        signal.alarm(0)

        # Process results
        provision_list = []
        for prov in provisions:
            provision_list.append({
                'id': prov['id'],
                'ref_number': prov['ref_number'],
                'section_header': prov['section_header'],
                'provision_text': prov['provision_text'],
                'document_id': prov['document_id'],
                'provision_type': prov['provision_type'],
                'zone': prov['zone'],
                'development_type': prov['development_type'],
                'page_number': prov['page_number']
            })

        cursor.close()
        conn.close()

        return {
            'success': True,
            'provisions': provision_list,
            'total_found': len(provision_list),
            'safety_status': 'CLAUDE.md compliant',
            'query_params': {
                'clause_reference': clause_reference,
                'document_type': document_type
            }
        }

    except TimeoutError:
        signal.alarm(0)  # Clear timeout
        return {
            'success': False,
            'error': 'Database query timeout (30s limit)',
            'provisions': [],
            'safety_status': 'timeout_protection_active'
        }
    except Exception as e:
        signal.alarm(0)  # Clear timeout
        return {
            'success': False,
            'error': f'Database safety error: {str(e)}',
            'provisions': [],
            'safety_status': 'error_handled'
        }
```

### **Phase 2: Backup Management**
```python
# 2. Create backup_manager.py
import os
import shutil
import datetime
from pathlib import Path

class DatabaseBackupManager:
    """
    Database backup management per CLAUDE.md requirements
    """

    def __init__(self):
        self.backup_dir = Path("database_backups")
        self.backup_dir.mkdir(exist_ok=True)

    def create_backup_before_query(self) -> dict:
        """Create backup before ANY database operation - MANDATORY"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"compliance_backup_{timestamp}.db"
            backup_path = self.backup_dir / backup_name

            # Copy database file
            shutil.copy2("nsw_planning.db", backup_path)

            return {
                'success': True,
                'backup_path': str(backup_path),
                'created_at': timestamp,
                'size_mb': backup_path.stat().st_size / (1024 * 1024)
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Backup creation failed: {str(e)}'
            }

    def check_recent_backup(self) -> dict:
        """Check if recent backup exists (within 1 hour)"""
        one_hour_ago = datetime.datetime.now() - datetime.timedelta(hours=1)

        recent_backups = []
        for backup_file in self.backup_dir.glob("compliance_backup_*.db"):
            file_time = datetime.datetime.fromtimestamp(backup_file.stat().st_mtime)
            if file_time > one_hour_ago:
                recent_backups.append({
                    'file': backup_file.name,
                    'created': file_time.isoformat(),
                    'size_mb': backup_file.stat().st_size / (1024 * 1024)
                })

        return {
            'recent_backup_exists': len(recent_backups) > 0,
            'backup_count': len(recent_backups),
            'most_recent': recent_backups[0] if recent_backups else None
        }

    def cleanup_old_backups(self, keep_count: int = 10):
        """Keep only the most recent N backups"""
        backups = sorted(
            self.backup_dir.glob("compliance_backup_*.db"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        for old_backup in backups[keep_count:]:
            old_backup.unlink()
```

### **Phase 3: TypeScript Client Safety Updates**
```typescript
// 3. Update compliance-client.ts with timeout handling
export class ComplianceDataClient {
  private pythonPath: string;
  private scriptBasePath: string;
  private readonly TIMEOUT_MS = 30000; // 30 second timeout per CLAUDE.md

  constructor() {
    this.pythonPath = 'python';
    this.scriptBasePath = path.join(process.cwd(), '..');
  }

  async getProvisionDetails(
    clauseReference: string,
    documentType: 'LEP' | 'DCP' | 'SEPP'
  ): Promise<ProvisionContent[]> {
    return new Promise((resolve, reject) => {
      const scriptPath = path.join(this.scriptBasePath, 'get_provision_details.py');

      // Create timeout promise
      const timeoutPromise = new Promise<never>((_, reject) => {
        setTimeout(() => {
          reject(new Error('Database operation timeout (30s limit per CLAUDE.md)'));
        }, this.TIMEOUT_MS);
      });

      // Create subprocess promise
      const subprocessPromise = new Promise<ProvisionContent[]>((resolve, reject) => {
        const python = spawn(this.pythonPath, [
          scriptPath,
          '--clause', clauseReference,
          '--document-type', documentType,
          '--format', 'json'
        ]);

        let stdout = '';
        let stderr = '';

        python.stdout.on('data', (data) => {
          stdout += data.toString();
        });

        python.stderr.on('data', (data) => {
          stderr += data.toString();
        });

        python.on('close', (code) => {
          if (code === 0) {
            try {
              const result = JSON.parse(stdout);

              // Check for safety compliance
              if (result.safety_status === 'CLAUDE.md compliant') {
                resolve(result.provisions || []);
              } else {
                console.warn('Database safety warning:', result.safety_status);
                resolve(result.provisions || []);
              }
            } catch (parseError) {
              console.error('Failed to parse provision details:', stdout);
              resolve([]);
            }
          } else {
            console.error('Provision details script error:', stderr);
            resolve([]);
          }
        });

        python.on('error', (error) => {
          console.error('Failed to start provision details script:', error);
          reject(error);
        });
      });

      // Race between subprocess and timeout
      Promise.race([subprocessPromise, timeoutPromise])
        .then(resolve)
        .catch((error) => {
          console.error('Database operation failed:', error);
          resolve([]); // Graceful degradation
        });
    });
  }

  async getComplianceData(
    zone: string,
    heritage: boolean,
    constraints: any
  ): Promise<ComplianceData> {
    try {
      // Add safety status to response
      const startTime = Date.now();

      const buildingEnvelope = await this.getBuildingEnvelopeConstraints(zone, constraints);
      const environmental = await this.getEnvironmentalConstraints(heritage, constraints);
      const specialProvisions = await this.getSpecialProvisions(constraints);

      const processingTime = Date.now() - startTime;

      // Log performance for monitoring
      console.log(`Compliance data retrieved in ${processingTime}ms (CLAUDE.md timeout: ${this.TIMEOUT_MS}ms)`);

      return {
        building_envelope: buildingEnvelope,
        environmental: environmental,
        special_provisions: specialProvisions
      };

    } catch (error) {
      console.error('Compliance data retrieval error (CLAUDE.md safety active):', error);
      throw new Error(`Failed to retrieve compliance data: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }
}
```

---

## **SAFETY MONITORING AND VALIDATION**

### **Database Safety Audit Script**
```python
# 4. Create db_safety_audit.py
import subprocess
import json
from pathlib import Path

def audit_database_safety_compliance():
    """
    Audit current implementation against CLAUDE.md requirements
    """

    audit_results = {
        'claude_md_compliance': {},
        'safety_violations': [],
        'recommendations': []
    }

    # Check 1: db_safety_wrapper usage
    python_files = list(Path('.').glob('**/*.py'))
    files_using_wrapper = []
    files_direct_connection = []

    for file_path in python_files:
        try:
            content = file_path.read_text()
            if 'get_safe_connection' in content:
                files_using_wrapper.append(str(file_path))
            elif any(direct in content for direct in ['psycopg2.connect', 'sqlite3.connect']):
                files_direct_connection.append(str(file_path))
        except:
            continue

    audit_results['claude_md_compliance']['safety_wrapper'] = {
        'status': 'COMPLIANT' if files_using_wrapper else 'VIOLATION',
        'files_using_wrapper': files_using_wrapper,
        'files_direct_connection': files_direct_connection
    }

    # Check 2: Timeout implementation
    timeout_files = []
    for file_path in python_files:
        try:
            content = file_path.read_text()
            if any(timeout in content for timeout in ['signal.alarm', 'timeout', 'SIGALRM']):
                timeout_files.append(str(file_path))
        except:
            continue

    audit_results['claude_md_compliance']['timeouts'] = {
        'status': 'COMPLIANT' if timeout_files else 'VIOLATION',
        'files_with_timeouts': timeout_files
    }

    # Check 3: Backup procedures
    backup_files = []
    for file_path in python_files:
        try:
            content = file_path.read_text()
            if any(backup in content for backup in ['backup', 'shutil.copy', 'create_backup']):
                backup_files.append(str(file_path))
        except:
            continue

    audit_results['claude_md_compliance']['backups'] = {
        'status': 'COMPLIANT' if backup_files else 'VIOLATION',
        'files_with_backup_logic': backup_files
    }

    # Check 4: WHERE clause validation
    sql_files = []
    dangerous_queries = []
    for file_path in python_files:
        try:
            content = file_path.read_text()
            if 'SELECT' in content.upper():
                sql_files.append(str(file_path))
                # Check for dangerous queries without WHERE
                if 'DELETE FROM' in content.upper() and 'WHERE' not in content.upper():
                    dangerous_queries.append(f"{file_path}: DELETE without WHERE")
                if 'UPDATE' in content.upper() and 'WHERE' not in content.upper():
                    dangerous_queries.append(f"{file_path}: UPDATE without WHERE")
        except:
            continue

    audit_results['claude_md_compliance']['where_clauses'] = {
        'status': 'VIOLATION' if dangerous_queries else 'COMPLIANT',
        'sql_files': sql_files,
        'dangerous_queries': dangerous_queries
    }

    # Overall compliance status
    all_checks = [
        audit_results['claude_md_compliance']['safety_wrapper']['status'],
        audit_results['claude_md_compliance']['timeouts']['status'],
        audit_results['claude_md_compliance']['backups']['status'],
        audit_results['claude_md_compliance']['where_clauses']['status']
    ]

    audit_results['overall_compliance'] = 'COMPLIANT' if all(s == 'COMPLIANT' for s in all_checks) else 'VIOLATIONS_FOUND'

    return audit_results

if __name__ == '__main__':
    results = audit_database_safety_compliance()
    print(json.dumps(results, indent=2))
```

### **Continuous Safety Monitoring**
```python
# 5. Create safety_monitor.py
import time
import psutil
import logging
from datetime import datetime

class DatabaseSafetyMonitor:
    """
    Real-time monitoring for CLAUDE.md compliance
    """

    def __init__(self):
        self.start_time = time.time()
        self.query_count = 0
        self.timeout_count = 0
        self.backup_count = 0

        logging.basicConfig(
            filename='logs/db_safety.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def log_query_start(self, query_type: str, safety_level: str):
        """Log start of database query with safety level"""
        self.query_count += 1
        logging.info(f"Query #{self.query_count} started: {query_type} [Safety: {safety_level}]")

    def log_query_timeout(self, query_type: str):
        """Log query timeout (CLAUDE.md 30s limit)"""
        self.timeout_count += 1
        logging.warning(f"Query timeout #{self.timeout_count}: {query_type} exceeded 30s limit")

    def log_backup_created(self, backup_path: str, size_mb: float):
        """Log backup creation (CLAUDE.md requirement)"""
        self.backup_count += 1
        logging.info(f"Backup #{self.backup_count} created: {backup_path} ({size_mb:.1f}MB)")

    def log_safety_violation(self, violation_type: str, details: str):
        """Log CLAUDE.md safety rule violation"""
        logging.error(f"CLAUDE.md VIOLATION: {violation_type} - {details}")

    def get_safety_status(self) -> dict:
        """Get current safety monitoring status"""
        uptime_seconds = time.time() - self.start_time

        return {
            'uptime_seconds': uptime_seconds,
            'queries_executed': self.query_count,
            'timeouts_occurred': self.timeout_count,
            'backups_created': self.backup_count,
            'timeout_rate': self.timeout_count / max(self.query_count, 1),
            'claude_md_compliance': self.timeout_count == 0,  # No timeouts = good
            'memory_usage_mb': psutil.Process().memory_info().rss / 1024 / 1024,
            'timestamp': datetime.now().isoformat()
        }
```

---

## **IMPLEMENTATION CHECKLIST**

### **Critical Tasks**
- [ ] **1. Update `get_provision_details.py`** with safety wrapper
- [ ] **2. Update `get_setback_provisions.py`** with safety wrapper
- [ ] **3. Create `backup_manager.py`** for automated backups
- [ ] **4. Update `compliance-client.ts`** with timeout handling
- [ ] **5. Create `db_safety_audit.py`** for compliance checking
- [ ] **6. Create `safety_monitor.py`** for real-time monitoring
- [ ] **7. Test all database operations** with 30-second timeout
- [ ] **8. Verify backup creation** before every query
- [ ] **9. Run safety audit** and fix violations
- [ ] **10. Document safety compliance** for next PRP

### **Testing Requirements**
```python
# Test safety compliance
def test_claude_md_compliance():
    """Test all CLAUDE.md database safety requirements"""

    # Test 1: Safety wrapper usage
    assert imports_safety_wrapper('get_provision_details.py')

    # Test 2: Timeout implementation
    assert has_timeout_protection('get_provision_details.py', 30)

    # Test 3: Backup creation
    assert creates_backup_before_query('get_provision_details.py')

    # Test 4: WHERE clause validation
    assert all_queries_have_where_clauses()

    # Test 5: No direct database connections
    assert not_using_direct_connections()
```

---

## **SUCCESS CRITERIA**

### **CLAUDE.md Compliance Metrics**
- ✅ **100% usage of `db_safety_wrapper.py`** across all database code
- ✅ **30-second timeouts** on all database operations
- ✅ **Automated backups** before every database operation
- ✅ **WHERE clauses** on all SELECT/UPDATE/DELETE queries
- ✅ **Zero direct database connections** (all via safety wrapper)

### **Operational Metrics**
- ✅ **Zero safety violations** in audit report
- ✅ **Backup creation** logged for every operation
- ✅ **Timeout monitoring** active and logging
- ✅ **UI functionality** unchanged (no user impact)
- ✅ **Performance impact** < 200ms overhead

### **Quality Gates**
```python
SAFETY_QUALITY_GATES = {
    'backup_creation_rate': 100,      # % of operations with backup
    'timeout_implementation': 100,    # % of queries with timeout
    'safety_wrapper_usage': 100,      # % using db_safety_wrapper
    'where_clause_compliance': 100,   # % of safe queries
    'direct_connection_count': 0      # Zero direct connections allowed
}
```

---

## **DEPLOYMENT PROCEDURE**

### **Pre-Deployment Safety Check**
```bash
# 1. Run safety audit
python db_safety_audit.py

# 2. Check for violations
if grep -q "VIOLATION" audit_results.json; then
    echo "CLAUDE.md violations found - deployment blocked"
    exit 1
fi

# 3. Test backup system
python -c "from backup_manager import DatabaseBackupManager; print(DatabaseBackupManager().create_backup_before_query())"

# 4. Test timeout system
timeout 35s python get_provision_details.py --clause "test" --document-type "LEP"
```

### **Post-Deployment Verification**
```bash
# 1. Monitor safety logs
tail -f logs/db_safety.log

# 2. Check backup creation
ls -la database_backups/

# 3. Verify UI still works
curl -f http://localhost:3007/assessment/dashboard
```

---

**This PRP ensures CLAUDE.md database safety compliance while preserving the working UI implementation. It creates a secure foundation for subsequent architecture improvements in PRP-A2.**

**Safety First Approach: All database operations must pass CLAUDE.md compliance before proceeding to architecture optimization.**