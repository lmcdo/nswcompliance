import pg from 'pg';
const { Pool } = pg;

const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

async function check() {
  const client = await pool.connect();

  // Get sample "descriptive" provisions from Marrickville Roof topic
  const result = await client.query(`
    SELECT
      id,
      v2_topic,
      v2_heritage_type,
      LEFT(provision_text, 150) as text_sample
    FROM regulatory_provisions
    WHERE v2_marker = 'heritage'
      AND v2_topic = 'Roof'
      AND document_id ILIKE '%Marrickville%'
      AND v2_heritage_type = 'descriptive'
    LIMIT 10
  `);

  console.log('Sample "descriptive" Roof provisions:');
  result.rows.forEach((row, i) => {
    console.log(`\n${i+1}. [${row.v2_topic}] ${row.v2_heritage_type}`);
    console.log(`   ${row.text_sample}...`);
  });

  client.release();
  await pool.end();
}

check().catch(console.error);
