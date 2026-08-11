#!/usr/bin/env tsx
import { getPool } from '../lib/database/pool-manager.js';

const pool = getPool();

async function testInsert() {
  const testInsert = `
    INSERT INTO sepp_structured_requirements (
      provision_id,
      requirement_category,
      applies_to,
      source_clause,
      extraction_confidence
    ) VALUES (
      34887,
      'exclusion',
      'CDC',
      'Test Clause 1.1',
      0.95
    )
    RETURNING id;
  `;

  try {
    const result = await pool.query(testInsert);
    console.log('✅ Test INSERT successful!');
    console.log(`   New record ID: ${result.rows[0].id}`);

    // Query it back
    const verify = await pool.query('SELECT * FROM sepp_structured_requirements WHERE id = $1', [result.rows[0].id]);
    console.log('✅ Verified record exists, ID:', verify.rows[0].id);

    // Delete test record
    await pool.query('DELETE FROM sepp_structured_requirements WHERE provision_id = 34887');
    console.log('✅ Test record cleaned up');

  } catch (error) {
    console.error('❌ Test INSERT failed:', error);
  } finally {
    await pool.end();
  }
}

testInsert();
