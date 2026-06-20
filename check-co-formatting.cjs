const { Pool } = require('./frontend-nextjs/node_modules/pg');

(async () => {
  const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false }
  });

  // Get provisions with C11, C12 etc from Marrickville
  const marrickville = await pool.query(`
    SELECT id, v2_part, v2_topic, provision_text
    FROM regulatory_provisions
    WHERE document_id LIKE '%Marrickville%'
      AND provision_text LIKE '%C11%'
    LIMIT 5
  `);

  console.log('Marrickville provisions containing "C11":');
  marrickville.rows.forEach(r => {
    console.log(`\n[${r.id}] Part ${r.v2_part}, Topic: ${r.v2_topic}`);
    const text = r.provision_text;
    // Find C11 and show context
    const idx = text.indexOf('C11');
    if (idx >= 0) {
      console.log(`  ...${text.substring(Math.max(0, idx - 20), idx + 80)}...`);
    }
  });

  // Check Ashfield too
  const ashfield = await pool.query(`
    SELECT id, v2_part, v2_topic, provision_text
    FROM regulatory_provisions
    WHERE document_id LIKE '%Ashfield%'
      AND (provision_text LIKE '%C1%' OR provision_text LIKE '%O1%')
    LIMIT 5
  `);

  console.log('\n\nAshfield provisions containing "C#" or "O#":');
  ashfield.rows.forEach(r => {
    console.log(`\n[${r.id}] Part ${r.v2_part}, Topic: ${r.v2_topic}`);
    const text = r.provision_text;
    // Find C or O markers
    const match = text.match(/[CO]\d+/);
    if (match) {
      const idx = text.indexOf(match[0]);
      console.log(`  ...${text.substring(Math.max(0, idx - 20), idx + 80)}...`);
    }
  });

  await pool.end();
})();
