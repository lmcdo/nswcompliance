# NSW Planning Database Dump - October 10, 2025

## Dump Details

**Filename:** `nsw_planning_full_20251010.backup`
**Location:** `C:\Users\lawre\downloads\solvyra\projects\compliance engine\compliance-engine\backups\`
**Size:** 11 MB (compressed)
**Format:** PostgreSQL Custom Format (v1.16-0)
**Compression:** gzip
**Created:** October 10, 2025 at 00:43:22

## Database Information

**Database Name:** `nsw_planning`
**PostgreSQL Version:** 17.6
**Total TOC Entries:** 336 objects
**Database Objects:** 177 (tables, sequences, views, functions, schemas)

## Contents Summary

### Schemas
- `public` - Main schema with planning provisions
- `authoritative` - Authoritative compliance data
- `versions` - Version control system

### Extensions
- `pg_trgm` - Trigram text search support

### Key Tables

**Authoritative Schema:**
- `nsw_properties` - NSW property data
- `planning_provisions` - Planning provisions with authority tiers
- `compliance_visual_aids` - Visual aids for compliance
- `hierarchy_resolution_cache` - Legal hierarchy cache
- `professional_guidance` - Professional guidance documents
- `property_provision_analysis` - Property-specific analysis
- `provision_authority_tiers` - Legal authority hierarchy

**Public Schema:**
- `control_codes` - Planning control codes
- `cross_reference_index` - Cross-reference indexing
- `contextual_guidance_real` - Contextual guidance data
- Plus many more tables (see full list with pg_restore --list)

### Key Functions
- `search_provisions_tier1(text, text, integer)` - Tier 1 ranked search
- `normalize_document_identifier(text)` - Document ID normalization
- `update_provision_categories()` - Category management
- `get_current_version()` - Version management
- `validate_version_reference()` - Version validation

## Restore Instructions

### Full Restore (creates new database)
```bash
# Create new database
createdb -U postgres nsw_planning_restore

# Restore from dump
pg_restore -U postgres -d nsw_planning_restore -v nsw_planning_full_20251010.backup
```

### Selective Restore (specific tables only)
```bash
# List all objects in dump
pg_restore --list nsw_planning_full_20251010.backup > restore_toc.txt

# Restore specific table
pg_restore -U postgres -d target_database -t planning_provisions nsw_planning_full_20251010.backup
```

### Schema-Only Restore
```bash
pg_restore -U postgres -d target_database --schema-only nsw_planning_full_20251010.backup
```

### Data-Only Restore
```bash
pg_restore -U postgres -d target_database --data-only nsw_planning_full_20251010.backup
```

## Verification

Dump integrity verified with:
```bash
pg_restore --list nsw_planning_full_20251010.backup
```

**Status:** ✅ Valid PostgreSQL custom format backup
**TOC Entries:** 336
**Compression:** gzip (verified)
**Exit Code:** 0 (success)

## Safety Checks Performed

✅ PostgreSQL health check passed
✅ Disk space verified (>1GB available)
✅ Database connection count OK (1 active)
✅ No database locks detected
✅ Backup directory infrastructure verified

## Use Cases

1. **Disaster Recovery** - Full database restoration
2. **Development/Testing** - Clone production data for testing
3. **Migration** - Move database to new server
4. **Archival** - Historical record of database state
5. **Selective Restore** - Restore specific tables or schemas

## Notes

- This is a **full dump** including schema, data, and database objects
- Custom format allows for selective restore and parallel processing
- Compressed with gzip for efficient storage
- Compatible with PostgreSQL 17.x and likely backward compatible to 12.x+
- Password required for restore: `postgres` (default development password)

## Related Files

- Previous dumps available in same directory with timestamps
- See `database_schema_complete.json` for schema documentation
- See `DATABASE_HEALTH_SCORECARD.md` for database health status

## Contact

For questions about this dump or restoration assistance, refer to:
- Database safety wrapper: `db_safety_wrapper.py`
- Safety check script: `scripts/db_safety_check.sh`
- Project documentation: `PLANNING.md`

---

**Backup Created By:** Database Safety System
**Date:** October 10, 2025
**Project:** NSW Planning Compliance Engine
