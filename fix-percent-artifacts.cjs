const { Pool } = require('./frontend-nextjs/node_modules/pg');

(async () => {
  const pool = new Pool({
    connectionString: 'postgresql://postgres.llzdrxywpziewrzudwhj:eDDIYq8ottiaO9ll@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres',
    ssl: { rejectUnauthorized: false }
  });

  console.log('Fixing %$ artifacts in provision text...\n');

  // Count before
  const before = await pool.query(`SELECT COUNT(*) FROM regulatory_provisions WHERE provision_text LIKE '%\%$%'`);
  console.log(`Provisions with %$ artifacts: ${before.rows[0].count}`);

  // Fix: Replace %$ with %
  const result = await pool.query(`
    UPDATE regulatory_provisions
    SET provision_text = REPLACE(provision_text, '%$', '%')
    WHERE provision_text LIKE '%\%$%'
  `);

  console.log(`✓ Fixed ${result.rowCount} provisions`);

  // Verify
  const after = await pool.query(`SELECT COUNT(*) FROM regulatory_provisions WHERE provision_text LIKE '%\%$%'`);
  console.log(`\nRemaining artifacts: ${after.rows[0].count}`);

  // Sample fixed provisions
  const samples = await pool.query(`
    SELECT id, document_id, LEFT(provision_text, 150) as sample
    FROM regulatory_provisions
    WHERE provision_text LIKE '%[0-9]%'
    AND document_id LIKE '%Marrickville%'
    LIMIT 3
  `);

  console.log('\nSample fixed provisions:');
  samples.rows.forEach(r => console.log(`  [${r.id}] ${r.sample}...`));

  await pool.end();
  console.log('\n✓ Complete');
})();
