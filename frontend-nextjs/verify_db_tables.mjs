import { getPool } from './lib/database/pool-manager.js';

const pool = getPool();

const requiredTables = [
  'contextual_guidance_real',
  'cross_reference_index',
  'housing_sepp_standards',
  'dcp_general_requirements',
  'regulatory_provisions'
];

try {
  console.log('Checking database connection and tables...\n');

  for (const table of requiredTables) {
    try {
      const result = await pool.query(`SELECT COUNT(*) as count FROM ${table} LIMIT 1`);
      console.log(`✓ ${table}: ${result.rows[0].count} rows`);
    } catch (err) {
      console.log(`✗ ${table}: ${err.message.split('\n')[0]}`);
    }
  }

  await pool.end();
  console.log('\n✓ Database verification complete.');
} catch (error) {
  console.error('✗ Database connection failed:', error.message);
  process.exit(1);
}
