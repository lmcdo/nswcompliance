import pg from 'pg';
const { Pool } = pg;

const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

async function check() {
  const client = await pool.connect();

  console.log('=== CHECKING C-NUMBER CONTROLS ===\n');

  // Roof controls that start with C1, C2, etc.
  const cControls = await client.query(`
    SELECT id, LEFT(provision_text, 150) as text
    FROM regulatory_provisions
    WHERE v2_marker = 'heritage'
      AND v2_topic = 'Roof'
      AND v2_heritage_type = 'control'
      AND document_id ILIKE '%Marrickville%'
      AND (provision_text ~ 'C\d{1,3}[\s\n]')
    LIMIT 10
  `);

  console.log(`Controls with C-numbers: ${cControls.rows.length}`);
  cControls.rows.forEach((r, i) => {
    console.log(`\n${i+1}. ${r.text}...`);
  });

  // Controls without C-numbers (matched by "must", "shall", etc.)
  const mustControls = await client.query(`
    SELECT id, LEFT(provision_text, 150) as text
    FROM regulatory_provisions
    WHERE v2_marker = 'heritage'
      AND v2_topic = 'Roof'
      AND v2_heritage_type = 'control'
      AND document_id ILIKE '%Marrickville%'
      AND NOT (provision_text ~ 'C\d{1,3}[\s\n]')
    LIMIT 5
  `);

  console.log(`\n\nControls without C-numbers (imperative verbs): ${mustControls.rows.length}`);
  mustControls.rows.forEach((r, i) => {
    console.log(`\n${i+1}. ${r.text}...`);
  });

  client.release();
  await pool.end();
}

check().catch(console.error);
