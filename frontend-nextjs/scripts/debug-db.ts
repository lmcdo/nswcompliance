#!/usr/bin/env tsx
import { getPool } from '../lib/database/pool-manager.js';

async function debug() {
  const pool = getPool();

  console.log(`[DEBUG] Database: ${process.env.PGDATABASE || process.env.DATABASE_NAME}`);
  console.log(`[DEBUG] Host: ${process.env.PGHOST || process.env.DATABASE_HOST}`);

  // Check if table exists
  const tableCheck = await pool.query(`
  SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name = 'sepp_structured_requirements'
  );
`);

console.log(`\nTable exists: ${tableCheck.rows[0].exists}`);

// Count records
const count = await pool.query('SELECT COUNT(*) as total FROM sepp_structured_requirements');
console.log(`Total records BEFORE: ${count.rows[0].total}`);

// Test INSERT
try {
  const result = await pool.query(`
    INSERT INTO sepp_structured_requirements (provision_id, source_clause, extraction_confidence)
    VALUES (34887, 'Test', 0.95)
    RETURNING id
  `);
  console.log(`✅ Test INSERT successful, ID: ${result.rows[0].id}`);

  const count2 = await pool.query('SELECT COUNT(*) as total FROM sepp_structured_requirements');
  console.log(`Total records AFTER INSERT: ${count2.rows[0].total}`);

  // Check in another connection
  const pool2 = getPool();
  const count3 = await pool2.query('SELECT COUNT(*) as total FROM sepp_structured_requirements');
  console.log(`Total records (pool2): ${count3.rows[0].total}`);

  await pool.query('DELETE FROM sepp_structured_requirements WHERE source_clause = $1', ['Test']);
  console.log('✅ Test cleanup successful');
} catch (error) {
  console.error('❌ Test INSERT failed:', error);
}

  await pool.end();
}

debug();
