# PRP-8B CHUNK 1: Authoritative Database Schema Creation

**SESSION SCOPE**: Database schema only (Lines 18-222 from PRP-8B) 
**DURATION**: Single session (~30-45 minutes) 
**DEPENDENCIES**: PostgreSQL connection working 
**ROLLBACK**: Drop authoritative schema if any failures 

---

## **SPECIFIC IMPLEMENTATION TARGET**

### **PRIMARY OBJECTIVE:**
Create the complete 7-table authoritative schema structure as specified in PRP-8B lines 18-222.

### **SCOPE BOUNDARIES:**
- **DO**: Create schema structure, tables, indexes, constraints
- **DON'T**: Migrate data, create API endpoints, build frontend components
- **DON'T**: Implement any other PRP-8B components

### **FILES TO REFERENCE:**
- `PRPs/PRP-8B_AUTHORITATIVE_COMPLIANCE_SYSTEM.md` (lines 18-222)
- Current PostgreSQL connection details in `DATABASE_LOCATIONS_AND_ACTIVE_FILES.md`

---

## **SUCCESS CRITERIA (BINARY VERIFICATION)**

### **Primary Success Metrics:**
1. **Schema exists**: `SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'authoritative'` returns 1 row
2. **7 tables created**: `SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'authoritative'` returns 7
3. **All indexes created**: `SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'authoritative'` >= 8
4. **Foreign keys working**: All constraint checks pass

### **Required Tables (EXACT NAMES):**
1. `authoritative.nsw_properties`
2. `authoritative.planning_provisions`
3. `authoritative.provision_authority_tiers`
4. `authoritative.property_provision_analysis`
5. `authoritative.compliance_visual_aids`
6. `authoritative.hierarchy_resolution_cache`
7. `authoritative.professional_guidance`

---

## **FAILURE ANTICIPATION & ERROR CHECKING**

### **Pre-Implementation Checks:**
```sql
-- Check 1: PostgreSQL connection
SELECT version();
-- Expected: PostgreSQL version string
-- Failure: "psql: error: connection to server failed"

-- Check 2: Database access
SELECT current_database();
-- Expected: "nsw_planning" 
-- Failure: "permission denied" or wrong database

-- Check 3: Schema creation permission
SELECT has_schema_privilege(current_user, 'public', 'CREATE');
-- Expected: true
-- Failure: false (insufficient permissions)

-- Check 4: No existing authoritative schema (clean state)
SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name = 'authoritative';
-- Expected: 0 (fresh start)
-- Warning if > 0: existing schema detected
```

### **During Implementation Error Checks:**

#### **Error Check 1: Schema Creation**
```sql
-- Test schema creation
CREATE SCHEMA IF NOT EXISTS authoritative;

-- Verify
SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'authoritative';
-- Expected: 1 row with 'authoritative'
-- Failure: 0 rows = schema creation failed
```

#### **Error Check 2: Table Creation Sequence**
```sql
-- After each table creation, verify:
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'authoritative' 
ORDER BY table_name;

-- Expected progression:
-- After table 1: 1 row
-- After table 2: 2 rows
-- ... 
-- After table 7: 7 rows

-- Failure Detection:
-- If count doesn't increment: table creation failed
-- If wrong table names: creation script error
```

#### **Error Check 3: Foreign Key Constraints**
```sql
-- Test constraint creation
SELECT 
 tc.table_name, 
 tc.constraint_name, 
 tc.constraint_type
FROM information_schema.table_constraints tc
WHERE tc.table_schema = 'authoritative'
AND tc.constraint_type = 'FOREIGN KEY';

-- Expected: Multiple FOREIGN KEY constraints
-- Failure: 0 rows = constraints failed to create
-- Failure: ERROR during constraint creation = reference table missing
```

#### **Error Check 4: Index Creation**
```sql
-- Verify all performance indexes
SELECT indexname, tablename 
FROM pg_indexes 
WHERE schemaname = 'authoritative'
ORDER BY tablename, indexname;

-- Expected: 8+ indexes (as specified in PRP-8B lines 214-221)
-- Failure: Less than 8 indexes = incomplete index creation
```

### **Common Failure Scenarios & Diagnosis:**

#### **Failure Scenario 1: Permission Denied**
```
ERROR: permission denied for schema public
DIAGNOSIS: Insufficient PostgreSQL privileges
SOLUTION: Check user permissions or use postgres superuser
ROLLBACK: No rollback needed (no changes made)
```

#### **Failure Scenario 2: Connection Lost During Creation**
```
ERROR: server closed the connection unexpectedly
DIAGNOSIS: Database connection timeout or server restart
SOLUTION: Reconnect and check partial schema state
ROLLBACK: DROP SCHEMA authoritative CASCADE;
```

#### **Failure Scenario 3: Constraint Violation**
```
ERROR: relation "authoritative.planning_provisions" does not exist
DIAGNOSIS: Table creation order wrong (foreign key before referenced table)
SOLUTION: Fix creation sequence in schema script
ROLLBACK: DROP SCHEMA authoritative CASCADE;
```

#### **Failure Scenario 4: Data Type Mismatch**
```
ERROR: type "jsonb" does not exist
DIAGNOSIS: PostgreSQL version too old (needs 9.4+)
SOLUTION: Upgrade PostgreSQL or use JSON instead of JSONB
ROLLBACK: DROP SCHEMA authoritative CASCADE;
```

---

## **IMPLEMENTATION PROCEDURE**

### **Step 1: Pre-flight Verification**
Execute all pre-implementation checks above. **STOP if any fail.**

### **Step 2: Create Schema Script**
Create file: `scripts/create_authoritative_schema_chunk1.sql`

### **Step 3: Execute with Error Checking**
```sql
-- Enable error reporting
\set ON_ERROR_STOP on
\set ECHO all

-- Execute schema creation
\i scripts/create_authoritative_schema_chunk1.sql

-- Immediate verification
SELECT 'VERIFICATION: Schema created' as status,
 (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'authoritative') as tables_created;
```

### **Step 4: Full Verification Suite**
```sql
-- Comprehensive post-creation checks
SELECT 'TEST 1: Schema exists' as test,
 CASE WHEN EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = 'authoritative')
 THEN 'PASS' ELSE 'FAIL' END as result;

SELECT 'TEST 2: Table count' as test,
 CASE WHEN (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'authoritative') = 7
 THEN 'PASS' ELSE 'FAIL - Got ' || COUNT(*) || ' tables' END as result
FROM information_schema.tables WHERE table_schema = 'authoritative';

SELECT 'TEST 3: Foreign keys' as test,
 CASE WHEN COUNT(*) > 0 THEN 'PASS - ' || COUNT() || ' constraints'
 ELSE 'FAIL - No foreign keys' END as result
FROM information_schema.table_constraints 
WHERE table_schema = 'authoritative' AND constraint_type = 'FOREIGN KEY';

SELECT 'TEST 4: Indexes' as test,
 CASE WHEN COUNT(*) >= 8 THEN 'PASS - ' || COUNT(*) || ' indexes'
 ELSE 'FAIL - Only ' || COUNT(*) || ' indexes' END as result
FROM pg_indexes WHERE schemaname = 'authoritative';
```

---

## **COMPLETION VERIFICATION**

### **Final Verification Command:**
```bash
./venv_linux/Scripts/python.exe -c "
import psycopg2
import json
from datetime import datetime

conn = psycopg2.connect(host='localhost', database='nsw_planning', user='postgres', password='postgres')
cur = conn.cursor()

# Test all requirements
tests = []

# Test 1: Schema exists
cur.execute(\"SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name = 'authoritative'\")
schema_count = cur.fetchone()[0]
tests.append(('Schema exists', schema_count == 1, f'Expected 1, got {schema_count}'))

# Test 2: 7 tables
cur.execute(\"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'authoritative'\")
table_count = cur.fetchone()[0]
tests.append(('Table count', table_count == 7, f'Expected 7, got {table_count}'))

# Test 3: Required tables exist
required_tables = [
 'nsw_properties', 'planning_provisions', 'provision_authority_tiers',
 'property_provision_analysis', 'compliance_visual_aids', 
 'hierarchy_resolution_cache', 'professional_guidance'
]

for table in required_tables:
 cur.execute(f\"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'authoritative' AND table_name = '{table}'\")
 exists = cur.fetchone()[0] == 1
 tests.append((f'Table {table}', exists, 'Missing' if not exists else 'Present'))

# Test 4: Foreign keys
cur.execute(\"SELECT COUNT(*) FROM information_schema.table_constraints WHERE table_schema = 'authoritative' AND constraint_type = 'FOREIGN KEY'\")
fk_count = cur.fetchone()[0]
tests.append(('Foreign keys', fk_count > 0, f'Expected >0, got {fk_count}'))

# Test 5: Indexes 
cur.execute(\"SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'authoritative'\")
index_count = cur.fetchone()[0]
tests.append(('Indexes', index_count >= 8, f'Expected >=8, got {index_count}'))

# Print results
print('CHUNK 1 VERIFICATION RESULTS:')
print('=' * 50)
all_passed = True
for test_name, passed, detail in tests:
 status = 'PASS' if passed else 'FAIL'
 print(f'{status:4} | {test_name:<25} | {detail}')
 if not passed:
 all_passed = False

print('=' * 50)
if all_passed:
 print(' ALL TESTS PASSED - CHUNK 1 COMPLETE')
 # Create completion marker
 with open('prp_checkpoints/CHUNK_1_SCHEMA_COMPLETE.marker', 'w') as f:
 json.dump({
 'chunk': 'PRP-8B-CHUNK-1',
 'completed_at': datetime.now().isoformat(),
 'tables_created': table_count,
 'verification_passed': True,
 'next_chunk': 'CHUNK_2_DATA_MIGRATION'
 }, f, indent=2)
 print(' Completion marker created')
else:
 print(' VERIFICATION FAILED - ROLLBACK REQUIRED')

conn.close()
"
```

---

## **ROLLBACK PROCEDURES**

### **Rollback Command (If Any Failure):**
```sql
-- Complete rollback - removes everything
DROP SCHEMA IF EXISTS authoritative CASCADE;

-- Verify rollback
SELECT COUNT(*) FROM information_schema.schemata WHERE schema_name = 'authoritative';
-- Expected: 0 (clean state restored)
```

### **Partial Rollback (Specific Failures):**
```sql
-- If only certain tables failed:
DROP TABLE IF EXISTS authoritative.table_that_failed CASCADE;

-- If only indexes failed:
DROP INDEX IF EXISTS authoritative.index_that_failed;
```

---

## **COMPLETION ARTIFACTS**

### **Files Created:**
- `scripts/create_authoritative_schema_chunk1.sql` - Schema creation script
- `prp_checkpoints/CHUNK_1_SCHEMA_COMPLETE.marker` - Completion verification

### **Database Objects Created:**
- Schema: `authoritative` 
- Tables: 7 (as listed above)
- Indexes: 8+ performance indexes
- Constraints: Foreign key relationships

### **Next Chunk Preparation:**
Upon successful completion, `CHUNK_2_DATA_MIGRATION.md` can be executed which will:
- Read from existing `public.regulatory_provisions` table
- Migrate data into new `authoritative.planning_provisions` table
- Apply 5-tier classification system

---

## **CRITICAL SUCCESS FACTORS**

1. **Single Focus**: Only create schema structure, nothing else
2. **Binary Verification**: All tests must return clear PASS/FAIL
3. **Complete Rollback**: Any failure = complete rollback and restart 
4. **Clean State**: Verify no existing authoritative schema before starting
5. **Error Logging**: Capture exact error messages for diagnosis

**Total Expected Time**: 30-45 minutes for implementation + verification