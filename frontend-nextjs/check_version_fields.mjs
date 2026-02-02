import { getPool } from './lib/database/pool-manager.js';

const pool = getPool();

try {
  // Check regulatory_provisions columns for version tracking
  const columns = await pool.query(`
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'regulatory_provisions'
      AND (column_name LIKE '%version%'
           OR column_name LIKE '%amendment%'
           OR column_name LIKE '%updated%'
           OR column_name LIKE '%modified%'
           OR column_name LIKE '%date%')
    ORDER BY column_name
  `);

  console.log('Version/Date columns in regulatory_provisions:');
  columns.rows.forEach(r => console.log(`  ${r.column_name}: ${r.data_type}`));

  // Sample some data
  const sample = await pool.query(`
    SELECT
      id,
      document_id,
      v2_last_updated,
      v2_version_number,
      extraction_date
    FROM regulatory_provisions
    WHERE v2_last_updated IS NOT NULL
       OR v2_version_number IS NOT NULL
       OR extraction_date IS NOT NULL
    LIMIT 5
  `);

  console.log('\nSample provisions with version data:');
  sample.rows.forEach(r => {
    console.log(`  ID ${r.id}: updated=${r.v2_last_updated}, version=${r.v2_version_number}, extracted=${r.extraction_date}`);
  });

  await pool.end();
} catch (error) {
  console.error('Error:', error.message);
  process.exit(1);
}
