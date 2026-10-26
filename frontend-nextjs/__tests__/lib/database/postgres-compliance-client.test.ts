/**
 * The compliance client must connect where the rest of the site does: Vercel sets PG* variables
 * (lib/database/pool-manager.ts). Before 2026-10-26 it read only DB_* / DATABASE_* and fell back to
 * 127.0.0.1, so /api/clause answered "connect ECONNREFUSED 127.0.0.1:5432" in production.
 */
const poolArgs: any[] = [];
jest.mock('pg', () => ({
  Pool: jest.fn().mockImplementation((cfg: any) => { poolArgs.push(cfg); return { on: jest.fn(), end: jest.fn() }; }),
}));

const KEYS = ['PGHOST', 'PGDATABASE', 'PGUSER', 'PGPASSWORD', 'PGPORT', 'DB_HOST', 'DATABASE_HOST', 'DATABASE_SSL'];
const saved: Record<string, string | undefined> = {};
beforeEach(() => { poolArgs.length = 0; for (const k of KEYS) { saved[k] = process.env[k]; delete process.env[k]; } });
afterEach(() => { for (const k of KEYS) { if (saved[k] === undefined) delete process.env[k]; else process.env[k] = saved[k]; } });

describe('PostgreSQLComplianceClient connects with the PG* variables Vercel sets', () => {
  it('uses PGHOST and friends, with SSL for a Supabase pooler host', () => {
    Object.assign(process.env, { PGHOST: 'aws-0.pooler.supabase.com', PGDATABASE: 'postgres', PGUSER: 'u', PGPASSWORD: 'p', PGPORT: '6543' });
    const { PostgreSQLComplianceClient } = require('@/lib/database/postgres-compliance-client');
    new PostgreSQLComplianceClient();
    const cfg = poolArgs[poolArgs.length - 1];
    expect(cfg).toMatchObject({ host: 'aws-0.pooler.supabase.com', database: 'postgres', user: 'u', password: 'p', port: 6543 });
    expect(cfg.ssl).toEqual({ rejectUnauthorized: false });
  });

  it('still honours the older DB_HOST when PGHOST is absent', () => {
    process.env.DB_HOST = 'db.local';
    const { PostgreSQLComplianceClient } = require('@/lib/database/postgres-compliance-client');
    new PostgreSQLComplianceClient();
    expect(poolArgs[poolArgs.length - 1].host).toBe('db.local');
  });
});

describe('DatabaseClient (lib/database/client.ts, used by /api/clause) connects with PG* too', () => {
  it('uses PGHOST with SSL for a Supabase pooler host', () => {
    Object.assign(process.env, { PGHOST: 'aws-0.pooler.supabase.com', PGUSER: 'u', PGPASSWORD: 'p', PGPORT: '6543', PGDATABASE: 'postgres' });
    const { DatabaseClient } = require('@/lib/database/client');
    new DatabaseClient();
    const cfg = poolArgs[poolArgs.length - 1];
    expect(cfg).toMatchObject({ host: 'aws-0.pooler.supabase.com', user: 'u', password: 'p', port: 6543, database: 'postgres' });
    expect(cfg.ssl).toEqual({ rejectUnauthorized: false });
  });
});
