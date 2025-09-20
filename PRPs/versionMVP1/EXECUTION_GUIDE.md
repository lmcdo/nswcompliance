# Version Management MVP - Complete Execution Guide

## 📋 Overview

This guide provides step-by-step instructions for executing the complete Version Management MVP with mandatory verification after each PRP.

## 🔧 Prerequisites

### System Requirements
- PostgreSQL 17+ running with `nsw_planning` database
- Python 3.8+ with required packages
- Access to compliance engine codebase
- API server capability (for PRP-V3 and V6 testing)

### Database Setup
```bash
# Ensure PostgreSQL is running
"C:\Program Files\PostgreSQL\17\bin\pg_ctl.exe" status -D "C:\Program Files\PostgreSQL\17\data"

# Test connection
python test_db_connection.py
```

## 🚀 Execution Process

### Phase 1: Dry Run Execution
**ALWAYS run dry run first to validate the setup:**

```bash
cd PRPs/versionMVP1
python execute_version_mvp.py
```

**Expected Output:**
```
VERSION MANAGEMENT MVP EXECUTION
Mode: DRY RUN
Started: 2024-XX-XX XX:XX:XX
============================================================

🚀 Executing PRP-V1: Database Foundation...
PRP-V1: STARTING
  DRY RUN: Would execute prp_v1_schema.sql
    🔍 Running PRP-V1 verification...
    ✅ PRP-V1 verification passed
✅ PRP-V1: Database Foundation completed successfully

🚀 Executing PRP-V2: Version Service...
[continues for all PRPs...]
```

### Phase 2: Implementation Files Creation

Based on dry run results, create missing implementation files:

#### PRP-V2: Service Files
```bash
# Create service directory if needed
mkdir -p services

# Copy service implementations from PRP-V2 documentation
# services/version_manager.py
# services/version_aware_query.py
```

#### PRP-V3: API Modifications
```bash
# Manually update api_server.py with version endpoints
# Refer to PRP-V3_API_INTEGRATION.md for specific changes
```

#### PRP-V4: Migration Script
```bash
# Copy migration script from PRP-V4 documentation
# migrate_to_versions.py
```

#### PRP-V5: Frontend Components
```bash
# Create frontend components (optional for MVP)
mkdir -p frontend-nextjs/components/version
mkdir -p frontend-nextjs/hooks
# Copy components from PRP-V5 documentation
```

### Phase 3: Production Execution

**⚠️ WARNING: This will modify your database**

```bash
# Backup database first
pg_dump -U postgres nsw_planning > nsw_planning_backup_$(date +%Y%m%d_%H%M%S).sql

# Execute with confirmation
python execute_version_mvp.py --execute
```

## 🔍 Verification Details

Each PRP includes **mandatory verification** that runs immediately after execution:

### PRP-V1 Verification
- ✅ Schema `versions` created
- ✅ Tables `document_versions` and `version_audit_log` exist
- ✅ Version columns added to existing tables
- ✅ Indexes created for performance
- ✅ Helper functions operational
- ✅ Audit triggers functioning

### PRP-V2 Verification
- ✅ Service modules import successfully
- ✅ VersionManager operations functional
- ✅ VersionAwareQuery methods working
- ✅ Database integration stable

### PRP-V3 Verification
- ✅ API health check passes
- ✅ Version parameters accepted
- ✅ Backward compatibility maintained
- ✅ Response headers include version info
- ✅ Edge cases handled gracefully

### PRP-V4 Verification
- ✅ All documents have version records
- ✅ 95%+ provisions linked to versions
- ✅ Data integrity maintained
- ✅ No orphaned references
- ✅ Version functions operational

### PRP-V5 Verification
- ✅ Frontend component files exist (if applicable)
- ✅ TypeScript syntax valid
- ✅ API integration functional
- ✅ Build configuration ready

### PRP-V6 End-to-End Verification
- ✅ Complete version workflow functional
- ✅ API queries return correct data
- ✅ Performance under 2 seconds
- ✅ Data consistency across system
- ✅ Integration scenarios working

## 📊 Success Criteria

### Critical Requirements (Must Pass)
1. **Database Foundation** - All schema objects created
2. **Service Layer** - Version management operational
3. **Data Migration** - 95%+ provisions versioned successfully
4. **Performance** - Version queries complete in <2 seconds

### Optional Requirements (MVP Flexible)
1. **API Integration** - Can be partially implemented
2. **Frontend Components** - Can be created later
3. **Advanced Features** - Not required for MVP

## 🔧 Troubleshooting

### Common Issues

#### Database Connection Errors
```bash
# Check PostgreSQL status
"C:\Program Files\PostgreSQL\17\bin\pg_ctl.exe" status -D "C:\Program Files\PostgreSQL\17\data"

# Restart if needed
"C:\Program Files\PostgreSQL\17\bin\pg_ctl.exe" restart -D "C:\Program Files\PostgreSQL\17\data"
```

#### Missing Service Files
```bash
# Copy from PRP documentation
cp PRPs/versionMVP1/PRP-V2_VERSION_SERVICE.md services/
# Extract code blocks and create .py files
```

#### API Server Not Running
```bash
# Start API server for verification
python api_server.py &
# Run verification
python verify_v3_api.py
```

#### Migration Verification Failures
```bash
# Check migration logs
cat migration_log_*.json

# Review data integrity
python verify_v4_migration.py

# Rollback if needed
python migrate_to_versions.py --rollback
```

## 📁 Generated Files

After successful execution:

### Verification Results
- `verify_v1_results.json` - Database verification
- `verify_v2_results.json` - Service verification
- `verify_v3_results.json` - API verification
- `verify_v4_results.json` - Migration verification
- `verify_v5_results.json` - Frontend verification
- `verify_v6_results.json` - End-to-end verification

### Execution Logs
- `mvp_execution_YYYYMMDD_HHMMSS.json` - Complete execution log
- `mvp_execution_checkpoint.json` - Recovery checkpoint
- `migration_log_YYYYMMDD_HHMMSS.json` - Migration details

### Database Objects
- `prp_v1_schema.sql` - Database schema script
- Version tables in `versions` schema
- Version columns in existing tables

## 🎯 Post-Execution Validation

### Manual Verification Steps

1. **Database Check:**
```sql
-- Verify version schema
SELECT * FROM versions.document_versions LIMIT 5;

-- Check provision linking
SELECT COUNT(*) as total, COUNT(version_id) as versioned
FROM regulatory_provisions;
```

2. **API Test:**
```bash
# Test version endpoints
curl "http://localhost:8000/api/provisions?version=current"
curl "http://localhost:8000/api/versions/current"
```

3. **Performance Test:**
```bash
# Run performance verification
python verify_v6_e2e.py
```

## 🔄 Rollback Procedure

If issues occur during execution:

```bash
# Stop execution
Ctrl+C

# Check logs
cat mvp_execution_*.json

# Rollback database changes
python migrate_to_versions.py --rollback

# Restore from backup if needed
psql -U postgres nsw_planning < nsw_planning_backup_YYYYMMDD_HHMMSS.sql
```

## ✅ Success Confirmation

When execution completes successfully, you should see:

```
🎉 END-TO-END VALIDATION PASSED
✨ Version Management MVP is ready for production!
   All critical systems are operational.

EXECUTION SUMMARY
================
Status: SUCCESS ✅
Steps executed: 6
Errors: 0
```

## 📞 Support

If you encounter issues:

1. Check verification result files for detailed error messages
2. Review execution logs for step-by-step progress
3. Verify prerequisites are met
4. Run individual verification scripts for targeted debugging

The MVP provides a solid foundation for comprehensive version management while maintaining backward compatibility with existing systems.