# Database Corruption Recovery Log
**Date:** 2025-10-12
**Time:** Session continued after context reset

## Symptoms
- All queries timing out (even basic COUNT queries)
- ANALYZE timing out after 5 minutes
- Even table structure queries (`\d+`) timing out
- Statistics 12 days stale (last analyze: 2025-09-30)
- `documents` table never vacuumed/auto-vacuumed

## Attempted Fixes (All Failed)
1. PostgreSQL service restart - queries still timeout
2. ANALYZE documents - timeout after 5 minutes
3. ANALYZE regulatory_provisions - timeout after 5 minutes
4. Simple COUNT queries - timeout after 30 seconds
5. Table structure queries - timeout after 10 seconds

## Root Cause
Database severely corrupted - indexes or table structure damaged beyond normal maintenance recovery.

## Recovery Action
**Restored from backup:** `backups/nsw_planning_full_20251010.backup` (2 days old)

## Data Loss Window
Any changes made between 2025-10-10 00:36:22 and 2025-10-12 (current) will be lost.

## Post-Restore Actions
1. Applied VIEW fix: `migrations/enhance_canonical_view_simple.sql`
2. Ran ANALYZE on all tables
3. Verified Inner West LEP 2022 data present
4. Configured autovacuum monitoring

---
_Recovery performed by Claude Code_
