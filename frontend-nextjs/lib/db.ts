/**
 * Database Connection Pool - Production-Grade Singleton
 *
 * Hot-Reload Safe: Uses globalThis to survive Next.js module reloads
 * Connection Pooling: Prevents exhaustion with configurable limits
 *
 * IMPORTANT: All API routes must import from this file
 * to prevent connection pool exhaustion
 *
 * NOTE: Use Supabase port 6543 (Transaction mode) for serverless,
 * NOT 5432 (Session mode) which has connection limits.
 */

import { Pool, PoolClient } from 'pg';

// Prevent multiple instances during Next.js hot reload
const globalForDb = globalThis as unknown as {
  pool: Pool | undefined;
};

/**
 * Get or create the singleton database connection pool
 * Survives Next.js hot reloads in development
 */
export function getPool(): Pool {
  if (!globalForDb.pool) {
    const isSupabase = process.env.PGHOST?.includes('supabase') || process.env.PGHOST?.includes('pooler');

    globalForDb.pool = new Pool({
      host: process.env.PGHOST || 'localhost',
      database: process.env.PGDATABASE || 'nsw_planning',
      user: process.env.PGUSER || 'postgres',
      password: process.env.PGPASSWORD || 'postgres',
      port: parseInt(process.env.PGPORT || '5432'),

      // Connection pool settings to prevent exhaustion
      max: 20, // Maximum number of clients in the pool
      idleTimeoutMillis: 30000, // Close idle clients after 30 seconds
      connectionTimeoutMillis: 10000, // Return error after 10 seconds if connection cannot be established

      // Keep-alive to prevent connection drops
      keepAlive: true,
      keepAliveInitialDelayMillis: 10000,

      // SSL for Supabase connections
      ssl: isSupabase ? { rejectUnauthorized: false } : undefined,
    });

    // Connection lifecycle monitoring
    globalForDb.pool.on('connect', () => {
      const pool = globalForDb.pool;
      if (pool) {
        console.log('[DB Pool] Client connected (total:', pool.totalCount, 'idle:', pool.idleCount, 'waiting:', pool.waitingCount, ')');
      }
    });

    globalForDb.pool.on('error', (err) => {
      console.error('[DB Pool] Unexpected error on idle client:', err);
    });

    globalForDb.pool.on('remove', () => {
      const pool = globalForDb.pool;
      if (pool) {
        console.log('[DB Pool] Client removed (total:', pool.totalCount, ')');
      }
    });

    console.log('[DB Pool] Initialized with max', globalForDb.pool.options.max, 'connections');
  }

  return globalForDb.pool;
}

/**
 * Execute a query with automatic client management
 *
 * @param text SQL query text
 * @param params Query parameters
 * @returns Query result
 */
export async function query(text: string, params?: any[]) {
  const pool = getPool();
  const start = Date.now();

  try {
    const res = await pool.query(text, params);
    const duration = Date.now() - start;

    if (duration > 1000) {
      console.warn(`[Database] Slow query (${duration}ms):`, text.substring(0, 100));
    }

    return res;
  } catch (error) {
    console.error('[Database] Query error:', error);
    throw error;
  }
}

/**
 * Get a client from the pool for transactions
 * IMPORTANT: Must call client.release() when done
 */
export async function getClient(): Promise<PoolClient> {
  const pool = getPool();
  const client = await pool.connect();
  return client;
}

/**
 * Execute a transaction with automatic rollback on error
 *
 * @param callback Function that receives a client and returns a Promise
 * @returns Result of the callback
 *
 * @example
 * const result = await transaction(async (client) => {
 *   await client.query('INSERT INTO ...');
 *   await client.query('UPDATE ...');
 *   return { success: true };
 * });
 */
export async function transaction<T>(
  callback: (client: PoolClient) => Promise<T>
): Promise<T> {
  const pool = getPool();
  const client = await pool.connect();

  try {
    await client.query('BEGIN');
    const result = await callback(client);
    await client.query('COMMIT');
    return result;
  } catch (error) {
    await client.query('ROLLBACK');
    console.error('[DB Transaction] Rolled back due to error:', error);
    throw error;
  } finally {
    client.release();
  }
}

// Short-lived cache for per-LGA valid zone lists (DQ-30). lep_zone_coverage
// changes only when an LGA is (re-)scraped, not per-request, so a request-rate
// query is wasted work — but it must stay a live query, not a committed
// constant, since which LGAs are onboarded changes independent of deploys.
const zoneCoverageCache = new Map<string, { zones: string[]; expiresAt: number }>();
const ZONE_COVERAGE_CACHE_MS = 5 * 60 * 1000;

/**
 * Get the current, live-scraped set of valid zone codes for an LGA from
 * lep_zone_coverage (DQ-30). Distinct from zone-translation.ts's legacy/current
 * alias map: this answers "what zones exist in LGA X today", not "what did
 * this legacy code become".
 *
 * @param lga - LGA name as stored in lep_zone_coverage (e.g. "Waverley")
 * @returns Array of current zone codes for that LGA, or [] if the LGA has no
 *          rows (not yet onboarded — callers should not treat this as "no
 *          zones exist", just "we haven't scraped it").
 */
export async function getValidZonesForLga(lga: string): Promise<string[]> {
  const cached = zoneCoverageCache.get(lga);
  if (cached && cached.expiresAt > Date.now()) {
    return cached.zones;
  }

  // is_complete = TRUE: same coverage gate every other lep_zone_coverage
  // consumer in this codebase already applies (see /api/lep/permissibility,
  // /api/permissibility/check) -- an interrupted scrape must not be treated
  // as "this is the complete valid zone list for the LGA."
  const result = await query(
    'SELECT zone FROM lep_zone_coverage WHERE lga = $1 AND is_complete = TRUE ORDER BY zone',
    [lga]
  );
  const zones = result.rows.map((row: { zone: string }) => row.zone);

  zoneCoverageCache.set(lga, { zones, expiresAt: Date.now() + ZONE_COVERAGE_CACHE_MS });
  return zones;
}

/**
 * Get pool health metrics
 */
export function getPoolStats() {
  const pool = globalForDb.pool;
  if (!pool) {
    return { initialized: false };
  }

  return {
    initialized: true,
    totalCount: pool.totalCount,
    idleCount: pool.idleCount,
    waitingCount: pool.waitingCount,
  };
}

/**
 * Close the connection pool
 * Only call this on application shutdown
 */
export async function closePool() {
  if (globalForDb.pool) {
    await globalForDb.pool.end();
    globalForDb.pool = undefined;
    console.log('[DB Pool] Closed');
  }
}
