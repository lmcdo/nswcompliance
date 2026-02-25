const { Pool } = require('pg');
const pool = new Pool({
  host: 'aws-0-ap-southeast-2.pooler.supabase.com',
  port: 6543,
  database: 'postgres',
  user: 'postgres.yfhrjvcdaybbmihbivpg',
  password: process.env.SUPABASE_DB_PASSWORD || 'Solvyra2024!',
  ssl: { rejectUnauthorized: false }
});

(async () => {
  try {
    // Find tables related to pattern book
    const tables = await pool.query(`
      SELECT table_name
      FROM information_schema.tables
      WHERE table_schema = 'public'
      AND (table_name LIKE '%pattern%' OR table_name LIKE '%exclusion%' OR table_name LIKE '%sepp_structured%')
    `);
    console.log('\n=== Pattern Book Related Tables ===');
    console.log(tables.rows);

    // Count by requirement_type in sepp_structured_requirements
    const counts = await pool.query(`
      SELECT requirement_type, COUNT(*) as count
      FROM sepp_structured_requirements
      GROUP BY requirement_type
      ORDER BY count DESC
    `);
    console.log('\n=== sepp_structured_requirements Counts ===');
    console.log(counts.rows);

    // Sample a few rows to see structure
    const sample = await pool.query(`
      SELECT id, requirement_type, provision_text, document_id
      FROM sepp_structured_requirements
      LIMIT 5
    `);
    console.log('\n=== Sample Rows ===');
    console.log(sample.rows);

    // Total count
    const total = await pool.query('SELECT COUNT(*) FROM sepp_structured_requirements');
    console.log('\nTotal rows in sepp_structured_requirements:', total.rows[0].count);

    // Check regulatory_provisions for Pattern Book related provisions
    const regProv = await pool.query(`
      SELECT COUNT(*)
      FROM regulatory_provisions
      WHERE document_id LIKE '%pattern%' OR document_id LIKE '%housing%'
    `);
    console.log('\nPattern/Housing provisions in regulatory_provisions:', regProv.rows[0].count);

    await pool.end();
  } catch (err) {
    console.error('Error:', err.message);
    process.exit(1);
  }
})();
