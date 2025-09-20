# Version Management MVP - Implementation PRPs

## Overview
This folder contains the granular technical implementation PRPs (Pre-Release Procedures) for the NSW Planning Documents Version Management MVP.

## Implementation Timeline: 6 Weeks

### Week 1-2: Foundation
- **PRP-V1**: Database Version Infrastructure
- **PRP-V2**: Version Service Layer

### Week 3-4: Integration
- **PRP-V3**: API Version Integration
- **PRP-V4**: Data Migration Pipeline

### Week 5-6: Frontend & Validation
- **PRP-V5**: Frontend Version Components
- **PRP-V6**: End-to-End Validation

## PRP Execution Order

1. **PRP-V1_DATABASE_FOUNDATION.md** - Create version tables and schema
2. **PRP-V2_VERSION_SERVICE.md** - Build version management service
3. **PRP-V3_API_INTEGRATION.md** - Add version awareness to APIs
4. **PRP-V4_MIGRATION_PIPELINE.md** - Migrate existing data
5. **PRP-V5_FRONTEND_INTEGRATION.md** - Add UI version components
6. **PRP-V6_VALIDATION_SUITE.md** - Complete system validation

## Verification Scripts

Each PRP has an accompanying verification script:
- `verify_v1_database.py` - Validates database schema
- `verify_v2_service.py` - Tests version service operations
- `verify_v3_api.py` - Checks API version parameters
- `verify_v4_migration.py` - Validates data migration
- `verify_v5_frontend.py` - Tests frontend components
- `verify_v6_e2e.py` - End-to-end validation

## Master Execution

Run all PRPs in sequence:
```bash
python execute_version_mvp.py
```

## Success Criteria

- ✅ Two-version tracking (current + previous)
- ✅ Version-aware API queries
- ✅ Frontend version indicators
- ✅ Zero downtime migration
- ✅ Performance <2s for version queries
- ✅ 100% backward compatibility

## Architecture Decisions

1. **Document-level versioning** (not provision-level) for MVP
2. **Two-version limit** (current + previous only)
3. **JSONB metadata** for future extensibility
4. **Boolean is_current flag** for performance
5. **Manual version creation** (no automation in MVP)