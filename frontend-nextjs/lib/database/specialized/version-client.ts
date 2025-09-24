/**
 * Version Management PostgreSQL Client
 * Replaces services/version_manager.py subprocess
 */

import { Pool } from 'pg';

export class VersionClient {
  private pool: Pool;

  constructor() {
    this.pool = new Pool({
      host: process.env.DATABASE_HOST || 'localhost',
      database: process.env.DATABASE_NAME || 'nsw_planning',
      user: process.env.DATABASE_USER || 'postgres',
      password: process.env.DATABASE_PASSWORD || 'postgres',
      port: parseInt(process.env.DATABASE_PORT || '5432'),
      max: 5, // Lower max for utility client
    });
  }

  async getSystemVersions(): Promise<{
    database: string;
    total_provisions: number;
    last_updated: string;
    migration_status: string;
    api_version: string;
  }> {
    const client = await this.pool.connect();
    try {
      // Get database statistics
      const statsResult = await client.query(`
        SELECT
          COUNT(*) as total_provisions,
          MAX(created_at) as last_updated
        FROM regulatory_provisions
      `);

      const stats = statsResult.rows[0];

      return {
        database: 'postgresql',
        total_provisions: parseInt(stats.total_provisions),
        last_updated: stats.last_updated || new Date().toISOString(),
        migration_status: 'postgresql_native',
        api_version: '2.0.0'
      };

    } finally {
      client.release();
    }
  }

  async close(): Promise<void> {
    await this.pool.end();
  }
}