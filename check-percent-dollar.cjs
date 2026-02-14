const { Pool } = require('./frontend-nextjs/node_modules/pg');

(async () => {
  const pool = new Pool({
    connectionString: 'postgresql://postgres.llzdrxywpziewrzudwhj:eDDIYq8ottiaO9ll@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres',
    ssl: { rejectUnauthorized: false }
  });

  console.log('Checking for %$ artifacts...\n');

  // Check for the exact pattern from user's example
  const samples = await pool.query(`
    SELECT id, document_id, provision_text
    FROM regulatory_provisions
    WHERE provision_text LIKE '%30 %$%'
       OR provision_text LIKE '%20 %$%'
       OR provision_text LIKE '%45 %$%'
       OR provision_text LIKE '%50 %$%'
    LIMIT 5
  `);

  console.log(`Found ${samples.rows.length} provisions with number+space+%$ pattern:`);

  samples.rows.forEach(r => {
    // Extract context around the %$
    const text = r.provision_text;
    const idx = text.search(/\d+ %\$/);
    if (idx >= 0) {
      const context = text.substring(Math.max(0, idx - 30), idx + 40);
      console.log(`\n[${r.id}]`);
      console.log(`  ...${context}...`);
    }
  });

  await pool.end();
})();
