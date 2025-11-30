/**
 * Database Connection Pool - Production-Grade Singleton
 *
 * Hot-Reload Safe: Uses globalThis to survive Next.js module reloads
 * Connection Pooling: Prevents exhaustion with configurable limits
 *
 * IMPORTANT: All API routes must import from this file
 * to prevent connection pool exhaustion
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
    // Determine if we need SSL (required for Supabase pooler)
    const rawDatabaseUrl = process.env.DATABASE_URL;
    const isSupabase = rawDatabaseUrl?.includes('supabase') ||
                       process.env.PGHOST?.includes('supabase');
    const isProduction = process.env.NODE_ENV === 'production';

    // For Supabase Supavisor (pooler), we need sslmode=require in the connection string
    // The pg library's SSL object alone doesn't work with Supavisor
    let connectionString = rawDatabaseUrl;
    if (connectionString && isSupabase && !connectionString.includes('sslmode=')) {
      connectionString = connectionString + (connectionString.includes('?') ? '&' : '?') + 'sslmode=require';
    }

    globalForDb.pool = new Pool({
      // Prefer DATABASE_URL for production (includes proper pooler format)
      connectionString: connectionString,
      // Fallback to individual vars for local development
      host: connectionString ? undefined : (process.env.PGHOST || 'localhost'),
      database: connectionString ? undefined : (process.env.PGDATABASE || 'nsw_planning'),
      user: connectionString ? undefined : (process.env.PGUSER || 'postgres'),
      password: connectionString ? undefined : (process.env.PGPASSWORD || 'postgres'),
      port: connectionString ? undefined : parseInt(process.env.PGPORT || '5432'),

      // Connection pool settings to prevent exhaustion
      max: 20, // Maximum number of clients in the pool
      idleTimeoutMillis: 30000, // Close idle clients after 30 seconds
      connectionTimeoutMillis: 10000, // Return error after 10 seconds if connection cannot be established

      // Keep-alive to prevent connection drops
      keepAlive: true,
      keepAliveInitialDelayMillis: 10000,

      // SSL config as backup (sslmode in URL is primary for Supabase)
      ssl: isProduction || isSupabase
        ? { rejectUnauthorized: false }
        : false,
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
