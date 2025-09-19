# MIGRATION EXECUTION MANDATE - CRITICAL ENFORCEMENT
**Created**: 2025-09-08 12:58 UTC  
**Priority**: NUCLEAR CRITICAL  
**Status**: MANDATORY EXECUTION REQUIRED

## 🚨 MIGRATION FAILURE ANALYSIS: 3x POSTGRESQL FAILURES

### **EXPLICIT POSTGRESQL SPECIFICATIONS IGNORED:**
- **166 explicit PostgreSQL mentions** in PRPs
- **Frontend configured for PostgreSQL** (DATABASE_NAME=nsw_planning)  
- **PRP-8D explicitly creates PostgreSQL schema** (authoritative.*)
- **All verification scripts should test PostgreSQL**

### **YET SYSTEM DEFAULTS TO SQLITE EVERY FUCKING TIME**

## 🎯 MANDATORY EXECUTION PROTOCOL

### **PHASE 1: EXECUTE BULLETPROOF MIGRATION ENGINE**
```bash
# EXACT COMMAND THAT MUST BE RUN:
cd "C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine"
python scripts/bulletproof_migration_engine.py

# VERIFICATION:
# Check migration_state.json shows migrated_entries > 0
# Check PostgreSQL authoritative.planning_provisions has data
```

### **PHASE 2: VERIFY POSTGRESQL DATA**
```bash
# MUST CONFIRM:
1. PostgreSQL authoritative.planning_provisions > 0 records
2. Frontend API returns data (not "no data" warnings)
3. Zone R2 returns setback provisions
4. ALL verification scripts point to PostgreSQL, NOT SQLite
```

### **PHASE 3: DISABLE SQLITE FALLBACKS**
```bash
# RENAME SQLite TO PREVENT ACCIDENTAL USE:
mv nsw_planning.db nsw_planning_BACKUP_DO_NOT_USE.db

# UPDATE ALL VERIFICATION SCRIPTS:
# Change sqlite3.connect('nsw_planning.db') to PostgreSQL connections
```

## 🔒 BULLETPROOF SAFEGUARDS

### **1. Migration Completion Verification**
- **MANDATORY**: migration_state.json shows migrated_entries > 22,000
- **MANDATORY**: PostgreSQL tables contain actual data
- **MANDATORY**: Frontend API returns provision data

### **2. Database Target Enforcement**  
- **ALL scripts MUST use PostgreSQL connections**
- **NO SQLite connections allowed in verification**
- **Frontend MUST connect to PostgreSQL only**

### **3. Completion Criteria**
- ✅ `curl localhost:3007/api/setbacks/calculate` with R2 returns data
- ✅ PostgreSQL query returns provisions: `SELECT COUNT(*) FROM authoritative.planning_provisions`
- ✅ Migration state shows: `"migrated_entries": 22000+`

## 🚨 ENFORCEMENT MEASURES

### **IF MIGRATION FAILS AGAIN:**
1. **MANUAL VERIFICATION**: Check each step individually
2. **FORCE POSTGRESQL**: Disable all SQLite connections
3. **STEP-BY-STEP EXECUTION**: Run migration phases one by one
4. **REAL-TIME MONITORING**: Watch PostgreSQL table counts during migration

### **FAILURE PREVENTION:**
- **NO COMPLETION MARKERS** until frontend returns actual data
- **NO "SUCCESS" STATUS** until PostgreSQL has 22,000+ provisions
- **VERIFY TARGET DATABASE** not source database
- **TEST PRODUCTION CONNECTIONS** not development connections

## 💎 THE BULLETPROOF GUARANTEE

**EXECUTE THIS EXACT SEQUENCE:**
```bash
1. python scripts/bulletproof_migration_engine.py
2. Verify: psql -c "SELECT COUNT(*) FROM authoritative.planning_provisions"
3. Test: curl localhost:3007/api/setbacks/calculate -d '{"property_zone":"R2"}'
4. Confirm: Response contains actual setback data, not "no data" warning
```

**ONLY MARK COMPLETE WHEN ALL 4 STEPS RETURN SUCCESSFUL DATA**

---
**This mandate ensures the 4th migration attempt WILL succeed by forcing verification of the actual target database and preventing SQLite fallbacks.**