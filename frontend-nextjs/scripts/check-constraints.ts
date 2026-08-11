#!/usr/bin/env tsx
import { getPool } from '../lib/database/pool-manager.js';

async function check() {
  const pool = getPool();

  const r = await pool.query(`
    SELECT column_name, is_nullable, data_type
    FROM information_schema.columns
    WHERE table_name='sepp_structured_requirements'
      AND column_name IN ('requirement_category','applies_to')
  `);

  console.log('=== Current Constraints ===\n');
  r.rows.forEach(row => {
    console.log(`${row.column_name}:`);
    console.log(`  Type: ${row.data_type}`);
    console.log(`  Nullable: ${row.is_nullable}`);
    console.log('');
  });

  await pool.end();
}

check();
