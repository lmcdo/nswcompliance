import { getPool } from './lib/database/pool-manager.js';

const pool = getPool();

try {
  // Check total provisions
  const total = await pool.query('SELECT COUNT(*) as count FROM regulatory_provisions');
  console.log(`Total regulatory_provisions: ${total.rows[0].count}`);

  // Check by document type
  const byDoc = await pool.query(`
    SELECT
      CASE
        WHEN document_id LIKE '%SEPP%' THEN 'SEPP'
        WHEN document_id LIKE '%LEP%' THEN 'LEP'
        WHEN document_id LIKE '%DCP%' THEN 'DCP'
        ELSE 'Other'
      END as doc_type,
      COUNT(*) as count
    FROM regulatory_provisions
    GROUP BY 1
    ORDER BY count DESC
  `);

  console.log('\nBy document type:');
  byDoc.rows.forEach(r => console.log(`  ${r.doc_type}: ${r.count}`));

  // Check cross_reference_index
  const crossRef = await pool.query('SELECT COUNT(*) as count FROM cross_reference_index');
  console.log(`\ncross_reference_index: ${crossRef.rows[0].count}`);

  // Check if table structure exists
  const columns = await pool.query(`
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = 'cross_reference_index'
    ORDER BY ordinal_position
    LIMIT 10
  `);

  console.log('\ncross_reference_index columns:');
  columns.rows.forEach(r => console.log(`  - ${r.column_name}`));

  await pool.end();
} catch (error) {
  console.error('Error:', error.message);
  process.exit(1);
}
