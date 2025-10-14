# Database Connection Pool Migration

**Status:** Phase 1 Complete (Critical Routes) - 2025-10-14
**Impact:** Fixed connection pool exhaustion causing browse route hangs
**Architecture:** Hot-reload-safe singleton pattern with monitoring

---

## Problem Statement

### Original Issue
Multiple API routes were each creating their own PostgreSQL connection pool, leading to:

1. **Connection Pool Exhaustion**
   - PostgreSQL max connections: ~100
   - Each route created a pool with max 10-20 connections
   - 10+ routes = 100-200 potential connections
   - Browse route (3 rapid calls) caused immediate exhaustion

2. **Hot Reload Duplication**
   - Next.js hot reload created new module instances
   - Module-level `let pool = new Pool()` created duplicate pools
   - Development leaked connections continuously

3. **Cascade Effects**
   - Assessment route made HTTP calls to other endpoints (which created more pools)
   - Network overhead + serialization for internal calls
   - Unpredictable failures under load

### Symptoms
- Infinite spinner on browse route dropdown
- API timeouts after multiple requests
- Server hangs requiring restart
- "Connection timeout" errors

---

## Solution Architecture

### 1. Hot-Reload-Safe Singleton (`lib/db.ts`)

```typescript
// Uses globalThis to survive Next.js hot reloads
const globalForDb = globalThis as unknown as {
  pool: Pool | undefined;
};

export function getPool(): Pool {
  if (!globalForDb.pool) {
    globalForDb.pool = new Pool({
      max: 20,                      // Max concurrent connections
      idleTimeoutMillis: 30000,     // Close idle after 30s
      connectionTimeoutMillis: 10000, // Fail after 10s if can't connect
      keepAlive: true,
    });

    // Connection lifecycle monitoring
    globalForDb.pool.on('connect', () => { ... });
    globalForDb.pool.on('error', (err) => { ... });
  }
  return globalForDb.pool;
}
```

**Key Features:**
- Single pool shared across all routes
- Survives hot reloads (globalThis scope)
- Connection monitoring built-in
- Configurable limits prevent exhaustion

### 2. Query Helper Functions

```typescript
// Simple query (auto-release)
export async function query(text: string, params?: any[]) {
  const pool = getPool();
  return await pool.query(text, params);
}

// Transaction with auto-rollback
export async function transaction<T>(
  callback: (client: PoolClient) => Promise<T>
): Promise<T> {
  const client = await getClient();
  try {
    await client.query('BEGIN');
    const result = await callback(client);
    await client.query('COMMIT');
    return result;
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  } finally {
    client.release();
  }
}

// Health monitoring
export function getPoolStats() {
  return {
    totalCount: pool.totalCount,
    idleCount: pool.idleCount,
    waitingCount: pool.waitingCount,
  };
}
```

---

## Migration Status

### ✅ Phase 1: Critical Routes (COMPLETE)

**Migrated Routes:**

| Route | Queries | Priority | Status |
|-------|---------|----------|--------|
| `/api/browse/documents` | 1 | High | ✅ Migrated |
| `/api/browse/toc` | 1 | High | ✅ Migrated |
| `/api/browse/section` | 2 | High | ✅ Migrated |
| `/api/compliance/constraints` | 5 | Critical | ✅ Migrated |
| `/api/heritage/hca-check` | 1 | Medium | ✅ Migrated |

**Commits:**
- `02502886` - Browse routes + initial singleton
- `23ec1863` - Hot-reload safety + critical routes

**Testing Results:**
```
✓ Browse Documents: 110 DCP docs (previously hung)
✓ Constraints API: Working (5 queries, <500ms)
✓ Heritage API: Point-in-polygon working
✓ Pool monitoring: Stats visible in logs
```

### 🔄 Phase 2: Frequently Used Routes (PENDING)

**Remaining Routes Creating Pools:**

| Route | Queries | Frequency | Impact |
|-------|---------|-----------|--------|
| `/api/provisions/control-codes` | 1-2 | Medium | Medium |
| `/api/provisions/cross-references` | 1-2 | Medium | Medium |
| `/api/provisions/zone-applicability` | 1-2 | Medium | Medium |
| `/api/provisions/[id]/complete` | 1 | Low | Low |
| `/api/documents/[id]` | 1-2 | Low | Low |
| `/api/documents/[id]/extract-section` | 1-2 | Low | Low |
| `/api/dcp/full-text` | 1 | Low | Low |
| `/api/lep/full-text` | 1 | Low | Low |

**Estimated Total:** 7-8 routes remaining

---

## Migration Procedure

### Step 1: Identify Route

```bash
# Find routes creating pools
powershell -Command "Get-ChildItem -Path 'frontend-nextjs\app\api' -Recurse -Filter '*.ts' | Select-String -Pattern 'new Pool\('"
```

### Step 2: Update Imports

**Before:**
```typescript
import { Pool } from 'pg';

const pool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  // ... config
});
```

**After:**
```typescript
import { query } from '@/lib/db';
// or for transactions:
import { query, getClient } from '@/lib/db';
```

### Step 3: Replace `pool.query()` Calls

**Simple Query:**
```typescript
// Before
const result = await pool.query('SELECT ...', [param]);

// After
const result = await query('SELECT ...', [param]);
```

**Manual Client Management:**
```typescript
// Before
const client = await pool.connect();
try {
  const result = await client.query('SELECT ...');
  // ...
} finally {
  client.release();
}

// After
const client = await getClient();
try {
  const result = await client.query('SELECT ...');
  // ...
} finally {
  client.release();
}
```

**Transaction:**
```typescript
// After (new helper)
const result = await transaction(async (client) => {
  await client.query('INSERT INTO ...');
  await client.query('UPDATE ...');
  return { success: true };
});
```

### Step 4: Test

```bash
# Test the specific route
curl -s http://localhost:3007/api/YOUR_ROUTE -X POST -H "Content-Type: application/json" -d '{"test":"data"}'

# Check logs for "[DB Pool] Initialized"
# Should only see ONE initialization, not multiple

# Monitor pool stats
curl -s http://localhost:3007/api/YOUR_ROUTE
# Check server logs for connection counts
```

### Step 5: Commit

```bash
git add frontend-nextjs/app/api/YOUR_ROUTE/route.ts
git commit -m "refactor: Migrate YOUR_ROUTE to singleton pool

Migrated YOUR_ROUTE to use shared connection pool.

- Replaced Pool import with query helper
- Removed pool instantiation
- Updated X query calls to use shared pool

Testing: ✓ Route functional, pool stats showing single instance"

git push origin clean-main
```

---

## Testing Strategy

### Manual Testing

1. **Test Individual Route:**
   ```bash
   curl http://localhost:3007/api/YOUR_ROUTE
   ```

2. **Check Pool Initialization:**
   - Should see `[DB Pool] Initialized` only ONCE per server start
   - Subsequent requests should NOT create new pools

3. **Test Under Load:**
   ```bash
   # Rapid fire 10 requests
   for i in {1..10}; do
     curl -s http://localhost:3007/api/YOUR_ROUTE &
   done
   wait
   ```

4. **Check Pool Stats:**
   - Look for `[DB Pool] Client connected (total: X idle: Y waiting: Z)` in logs
   - Total should stay under 20
   - No connection timeout errors

### Automated Testing (Future)

```typescript
// test/db-pool.test.ts
import { getPool, getPoolStats } from '@/lib/db';

describe('Database Pool', () => {
  it('should create only one pool instance', () => {
    const pool1 = getPool();
    const pool2 = getPool();
    expect(pool1).toBe(pool2);
  });

  it('should provide health stats', () => {
    const stats = getPoolStats();
    expect(stats.initialized).toBe(true);
    expect(stats.totalCount).toBeLessThanOrEqual(20);
  });
});
```

---

## Monitoring & Debugging

### Check Pool Health

**During Development:**
```typescript
// Add to any route for debugging
import { getPoolStats } from '@/lib/db';

console.log('[Route Debug] Pool stats:', getPoolStats());
```

**Server Logs:**
```
[DB Pool] Initialized with max 20 connections
[DB Pool] Client connected (total: 1 idle: 0 waiting: 0)
[DB Pool] Client connected (total: 2 idle: 1 waiting: 0)
[DB Pool] Client removed (total: 1)
```

### Warning Signs

⚠️ **Multiple Initializations:**
```
[DB Pool] Initialized with max 20 connections
[DB Pool] Initialized with max 20 connections  // BAD - indicates duplicate pool
```
**Fix:** Route not using shared pool, still creating its own

⚠️ **High Connection Count:**
```
[DB Pool] Client connected (total: 19 idle: 0 waiting: 5)
```
**Fix:** Connections not being released, check for missing `client.release()`

⚠️ **Connection Timeouts:**
```
[DB Pool] Error: Connection timeout after 10000ms
```
**Fix:** Pool exhausted, increase max connections or fix connection leaks

---

## Performance Benchmarks

### Before Migration (Browse Route)
```
First call:  Hang (timeout after 10s)
Second call: Hang (timeout after 10s)
Third call:  Server restart required
```

### After Migration (Browse Route)
```
Documents:   <100ms (110 docs)
TOC:         ~16ms (12 sections)
Section:     <50ms (variable provisions)

Sequential: No hangs, consistent performance
Parallel:   10 concurrent requests handled smoothly
```

### Resource Usage

**Before:**
- 10+ connection pools
- 100-200 potential connections
- Memory leak during hot reload

**After:**
- 1 connection pool
- Max 20 connections
- Stable memory usage

---

## Architecture Decisions

### Why globalThis?

**Problem:** Next.js hot reload creates new module instances
```typescript
// Module-level variable (WRONG)
let pool: Pool | null = null;

// Hot reload sequence:
// 1. File changes → creates new module
// 2. New module has NEW pool variable
// 3. Old pool still exists (leaked)
```

**Solution:** globalThis survives module reloads
```typescript
const globalForDb = globalThis as unknown as { pool: Pool | undefined };

// Hot reload sequence:
// 1. File changes → creates new module
// 2. New module checks globalThis.pool
// 3. Existing pool found → reused
```

### Why Not Database Connection Per Request?

**Considered:** Create connection for each request
- ❌ Connection overhead (100-200ms each)
- ❌ PostgreSQL connection limit
- ❌ No connection reuse

**Chosen:** Connection pooling
- ✅ Fast (reuse existing connections)
- ✅ Configurable limits
- ✅ Industry standard

### Why Not Use ORM (Prisma, TypeORM)?

**Pros of raw pg:**
- Full SQL control (complex queries)
- Better performance for read-heavy workload
- Existing codebase already uses pg
- Simpler debugging (see exact SQL)

**Cons:**
- Manual query writing
- No type safety on queries (can add with tools later)

**Decision:** Keep pg, enhance with shared pool

---

## Known Issues

### Issue 1: Assessment Route HTTP Calls

**Current:**
```typescript
// assessment/route.ts makes HTTP call to itself
const response = await fetch(
  'http://localhost:3000/api/compliance/enhanced',
  { method: 'POST', body: JSON.stringify(data) }
);
```

**Problem:**
- Extra network overhead
- Serialization/deserialization
- That endpoint creates its own pool

**Future Fix:** Create service layer
```typescript
// lib/services/compliance-service.ts
export async function getEnhancedCompliance(params) {
  // Direct function call, shared pool
  return await query('SELECT ...', params);
}

// assessment/route.ts
import { getEnhancedCompliance } from '@/lib/services/compliance-service';
const compliance = await getEnhancedCompliance(params);
```

**Status:** Deferred to Phase 3

### Issue 2: Documents API Slow Query

**Route:** `/api/browse/documents`
**Symptom:** Sometimes times out (5s)
**Cause:** Slow query checking TOC existence for all documents

**Current Query:**
```sql
SELECT
  p.document_id,
  EXISTS(SELECT 1 FROM dcp_table_of_contents t WHERE t.document_id = p.document_id) as has_toc,
  COUNT(p.id) as provision_count
FROM regulatory_provisions p
GROUP BY p.document_id
```

**Future Optimization:**
- Add materialized view
- Cache results
- Add index on dcp_table_of_contents.document_id (already exists)

**Status:** Monitoring

---

## Future Enhancements

### 1. Health Check Endpoint

```typescript
// app/api/health/db/route.ts
import { getPoolStats, query } from '@/lib/db';

export async function GET() {
  try {
    const stats = getPoolStats();
    const result = await query('SELECT 1');

    return NextResponse.json({
      status: 'healthy',
      pool: stats,
      database: 'connected'
    });
  } catch (error) {
    return NextResponse.json({
      status: 'unhealthy',
      error: error.message
    }, { status: 503 });
  }
}
```

### 2. Query Performance Monitoring

```typescript
// Add to query() function
export async function query(text: string, params?: any[]) {
  const start = Date.now();
  try {
    const res = await pool.query(text, params);
    const duration = Date.now() - start;

    // Log slow queries
    if (duration > 1000) {
      console.warn(`[DB] Slow query (${duration}ms):`, text.substring(0, 100));
    }

    // Track metrics (could send to monitoring service)
    metrics.recordQueryDuration(duration);

    return res;
  } catch (error) {
    metrics.recordQueryError();
    throw error;
  }
}
```

### 3. Read Replica Support

```typescript
// lib/db.ts
export function getReadPool(): Pool {
  if (!globalForDb.readPool) {
    globalForDb.readPool = new Pool({
      host: process.env.READ_REPLICA_HOST,
      // ... config
    });
  }
  return globalForDb.readPool;
}

// Usage
import { query } from '@/lib/db'; // writes
import { getReadPool } from '@/lib/db'; // reads

const readPool = getReadPool();
const result = await readPool.query('SELECT ...'); // read from replica
```

---

## Reference Links

### Documentation
- [node-postgres Connection Pooling](https://node-postgres.com/features/pooling)
- [Next.js Hot Reload](https://nextjs.org/docs/architecture/fast-refresh)
- [PostgreSQL Connection Limits](https://www.postgresql.org/docs/current/runtime-config-connection.html)

### Related Issues
- Browse route hanging: Fixed in commit `02502886`
- Hot reload duplication: Fixed in commit `23ec1863`

### Code Locations
- Singleton pool: `frontend-nextjs/lib/db.ts`
- Browse routes: `frontend-nextjs/app/api/browse/`
- Constraints: `frontend-nextjs/app/api/compliance/constraints/route.ts`
- Heritage: `frontend-nextjs/app/api/heritage/hca-check/route.ts`

---

## Changelog

### 2025-10-14 - Phase 1 Complete
- Created hot-reload-safe singleton pool (`lib/db.ts`)
- Migrated browse routes (documents, toc, section)
- Migrated constraints route (5 queries)
- Migrated heritage HCA check route
- Added connection lifecycle monitoring
- Added transaction helper
- Added pool health stats
- Tested and verified all routes functional
- Documented architecture and migration process

### Future Entries
_Add updates here as Phase 2 progresses_

---

## Contributors

- Migration initiated: 2025-10-14
- Primary implementation: Claude Code
- Testing: Manual verification of critical routes
- Documentation: This file

---

**Last Updated:** 2025-10-14
**Next Review:** After Phase 2 migration or when issues arise
