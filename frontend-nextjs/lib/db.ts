/**
 * Database Connection Pool - Singleton
 *
 * IMPORTANT: All API routes must import from this file
 * to prevent connection pool exhaustion
 */

import { Pool } from 'pg';

// Singleton pool instance
let pool: Pool | null = null;

/**
 * Get or create the singleton database connection pool
 */
export function getPool(): Pool {
  if (!pool) {
    pool = new Pool({
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
    });

    // Log pool errors
    pool.on('error', (err) => {
      console.error('[Database Pool] Unexpected error on idle client', err);
    });

    console.log('[Database Pool] Initialized with max', pool.options.max, 'connections');
  }

  return pool;
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
export async function getClient() {
  const pool = getPool();
  const client = await pool.connect();

  return client;
}

/**
 * Close the connection pool
 * Only call this on application shutdown
 */
export async function closePool() {
  if (pool) {
    await pool.end();
    pool = null;
    console.log('[Database Pool] Closed');
  }
}
