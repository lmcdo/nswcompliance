# Database Cleanup Tasks

Created: 2026-02-11

## Verification Results (Step 1)

**Database Size:** 330 MB

### Backup Tables (ALL SAFE TO DROP)
| Table | Rows | Status |
|-------|------|--------|
| dcp_general_provisions_backup_r1_fix | 130 | ✓ |
| dcp_general_provisions_corrupted_f1_backup | 7 | ✓ |
| dcp_general_requirements_backup_20251030 | 555 | ✓ |
| dcp_general_requirements_old_broad_linking | 189 | ✓ |
| dcp_precinct_boundaries_backup_20251109_152059 | 85 | ✓ |
| dcp_precinct_boundaries_backup_polygon | 46 | ✓ |
| dcp_precinct_boundaries_backup_rename_20251109_153810 | 5 | ✓ |
| dcp_precinct_requirements_backup_page_fix | 265 | ✓ |
| document_id_backup | 47818 | ✓ |

### Empty Unused Tables (SAFE TO DROP)
| Table | Rows |
|-------|------|
| categorization_validation | 0 |
| dcp_base_requirements | 0 |
| dcp_precinct_metadata | 0 |
| provision_diagrams | 0 |

### Duplicate/Obsolete Tables
| Table | Check | Result |
|-------|-------|--------|
| precinct_boundaries | 13/13 match dcp_precinct_boundaries | ✓ SAFE TO DROP |
| regulatory_refs_core | 762/762 in regulatory_refs | ✓ SAFE TO DROP |
| development_pathways | 1 row (test data) | ✓ SAFE TO DROP |

### Tables to KEEP
| Table | Rows | Reason |
|-------|------|--------|
| requirement_metrics | 0 | Part of /api/feedback/requirement |
| requirement_review_queue | 0 | Part of /api/feedback/requirement |

---

## Code Changes Made

| File | Change |
|------|--------|
| `frontend-nextjs/lib/database/client.ts` | Removed `development_pathways` COUNT query |
| `frontend-nextjs/lib/database/postgres-client.ts` | Removed `development_pathways` COUNT query |
| `frontend-nextjs/lib/database/mock-client.ts` | Removed `development_pathways` mock value |
| `frontend-nextjs/lib/precinct-service.ts` | Fixed comment to reference `dcp_precinct_boundaries` |

---

## How to Execute Cleanup

### Option 1: Run SQL in Supabase SQL Editor
Copy and paste from `scripts/db_cleanup_final.sql` (Steps 2-5)

### Option 2: Quick Drop Commands
```sql
-- Backup tables
DROP TABLE IF EXISTS dcp_general_provisions_backup_r1_fix;
DROP TABLE IF EXISTS dcp_general_provisions_corrupted_f1_backup;
DROP TABLE IF EXISTS dcp_general_requirements_backup_20251030;
DROP TABLE IF EXISTS dcp_general_requirements_old_broad_linking;
DROP TABLE IF EXISTS dcp_precinct_boundaries_backup_20251109_152059;
DROP TABLE IF EXISTS dcp_precinct_boundaries_backup_polygon;
DROP TABLE IF EXISTS dcp_precinct_boundaries_backup_rename_20251109_153810;
DROP TABLE IF EXISTS dcp_precinct_requirements_backup_page_fix;
DROP TABLE IF EXISTS document_id_backup;

-- Empty unused
DROP TABLE IF EXISTS categorization_validation;
DROP TABLE IF EXISTS dcp_base_requirements;
DROP TABLE IF EXISTS dcp_precinct_metadata;
DROP TABLE IF EXISTS provision_diagrams;

-- Duplicates
DROP TABLE IF EXISTS precinct_boundaries;
DROP TABLE IF EXISTS regulatory_refs_core;
DROP TABLE IF EXISTS development_pathways;

-- Reclaim space
VACUUM FULL;
```

---

## Expected Outcome

- **Tables dropped:** 16
- **Estimated space saved:** 5-10 MB
- **Remaining tables:** ~42 (from 58)

---

## Files in This Folder

- `README.md` - This file
- `verify_cleanup_state.mjs` - Verification script (run from frontend-nextjs)

## Related Files

- `scripts/db_cleanup_final.sql` - Full SQL script with all steps
- `scripts/db_cleanup_investigation.sql` - Investigation queries
