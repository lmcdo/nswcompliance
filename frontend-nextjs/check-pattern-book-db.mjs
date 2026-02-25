import { getPool } from './lib/database/pool-manager.ts';

(async () => {
  try {
    console.log('=== SEARCHING FOR PATTERN BOOK DATA ===\n');

    const pool = getPool();

    // Find tables
    const tables = await pool.query(`
      SELECT table_name
      FROM information_schema.tables
      WHERE table_schema = 'public'
      AND (table_name LIKE '%pattern%' OR table_name LIKE '%exclusion%' OR table_name LIKE '%sepp_structured%')
    `);
    console.log('Pattern Book Related Tables:');
    console.log(tables.rows.length ? tables.rows : 'None found');

    // Count sepp_structured_requirements
    const counts = await pool.query(`
      SELECT requirement_type, COUNT(*) as count
      FROM sepp_structured_requirements
      GROUP BY requirement_type
      ORDER BY count DESC
    `);
    console.log('\nsepp_structured_requirements by type:');
    counts.rows.forEach(r => console.log(`  ${r.requirement_type}: ${r.count}`));

    const total = await pool.query('SELECT COUNT(*) FROM sepp_structured_requirements');
    console.log(`\nTotal: ${total.rows[0].count} rows`);

    // Check regulatory_provisions for Housing SEPP
    const housing = await pool.query(`
      SELECT COUNT(*)
      FROM regulatory_provisions
      WHERE document_id LIKE '%Housing%2021%'
    `);
    console.log(`\nHousing SEPP 2021 provisions in regulatory_provisions: ${housing.rows[0].count}`);

    await pool.end();
    process.exit(0);
  } catch (err) {
    console.error('Error:', err.message);
    process.exit(1);
  }
})();
