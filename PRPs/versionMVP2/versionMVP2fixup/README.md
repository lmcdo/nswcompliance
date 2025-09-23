# Version MVP2 Fixup PRPs

## Overview
Granular technical implementation PRPs to fix the 4 critical issues blocking Version Management MVP2 completion.

## Issues Addressed

### 1. **PRP-F1: Foreign Key Constraint Fix**
- **Problem**: V5 foreign key constraint errors in provision_changes table
- **Solution**: Analyze and repair constraint violations, create validation functions
- **Script**: `verify_f1_foreign_key_fix.py`

### 2. **PRP-F2: Metadata Validation Fix**
- **Problem**: V7 Pydantic expects dict but gets None for metadata fields
- **Solution**: Fix database defaults and Pydantic model validation
- **Script**: `verify_f2_metadata_validation.py`

### 3. **PRP-F3: API Port Detection Fix**
- **Problem**: Verification scripts hardcoded to port 8000, API runs on 8006
- **Solution**: Dynamic port detection and configuration management
- **Script**: `verify_f3_api_port_detection.py`

### 4. **PRP-F4: Provision Linking Completion**
- **Problem**: 10K provisions (44,210 - 34,290) still unlinked to versions
- **Solution**: Fuzzy matching and document identifier normalization
- **Script**: `verify_f4_provision_linking.py`

## Execution

### Quick Start
```bash
cd "PRPs/versionMVP2/versionMVP2fixup"
python execute_all_fixes.py
```

### Individual PRPs
```bash
# Fix foreign key constraints
python verify_f1_foreign_key_fix.py

# Fix metadata validation
python verify_f2_metadata_validation.py

# Fix API port detection
python verify_f3_api_port_detection.py

# Complete provision linking
python verify_f4_provision_linking.py
```

## Dependencies

### System Requirements
- PostgreSQL running with nsw_planning database
- Python 3.7+ with psycopg2, requests
- API server running (for F3 testing)

### Execution Order
1. **F1, F2, F3** can run in parallel (no dependencies)
2. **F4** should run after F1 and F2 (needs database fixes)

## Success Criteria

### PRP-F1 Success
- ✅ All foreign key constraints validated
- ✅ No orphaned provision_changes records
- ✅ Change tracking functionality working

### PRP-F2 Success
- ✅ All metadata fields have valid dict values
- ✅ Pydantic validation passes
- ✅ Database defaults set correctly

### PRP-F3 Success
- ✅ API server automatically detected
- ✅ All verification scripts work with actual API
- ✅ Dynamic port configuration supported

### PRP-F4 Success
- ✅ >95% provisions linked (42,000+ out of 44,210)
- ✅ Document matching accuracy >90%
- ✅ Fuzzy matching for edge cases

## Results

Each PRP generates a detailed JSON results file:
- `verify_f1_results.json` - Foreign key fix results
- `verify_f2_results.json` - Metadata validation results
- `verify_f3_results.json` - API detection results
- `verify_f4_results.json` - Provision linking results
- `execute_all_fixes_results.json` - Master execution summary

## Verification

After running all fixes, the original MVP2 verification scripts should pass:
```bash
cd "../"
python verify_v5_enhanced.py  # Should pass after F1
python verify_v7_enhanced.py  # Should pass after F2
python verify_v6_enhanced.py  # Should pass after F3
python verify_v4_enhanced.py  # Should pass after F4
```

## Architecture

### Database Fixes (F1, F2)
- Repair data integrity issues
- Add missing constraints and defaults
- Create validation helper functions

### Infrastructure Fixes (F3)
- Dynamic service discovery
- Configuration file support
- Environment variable support

### Data Completion (F4)
- Advanced document matching algorithms
- Fuzzy string matching with PostgreSQL pg_trgm
- Automated version creation for orphaned documents

## Troubleshooting

### Common Issues
1. **Database connection errors**: Check PostgreSQL is running on port 5432
2. **Permission errors**: Ensure user has CREATE/ALTER privileges
3. **Missing extensions**: Install pg_trgm for fuzzy matching
4. **API not found**: Start api_server.py before running F3

### Debug Mode
Add `--debug` flag to any verification script for verbose output:
```bash
python verify_f1_foreign_key_fix.py --debug
```

## Integration

These fixup PRPs integrate with the main Version Management system:
- Fix blocking issues preventing MVP2 completion
- Enable full end-to-end verification
- Prepare system for production deployment

After successful completion, the NSW Planning Compliance Engine will have:
- ✅ 44,210 provisions with version management
- ✅ 102+ document versions with baseline tracking
- ✅ Working API endpoints with version awareness
- ✅ Robust change tracking infrastructure