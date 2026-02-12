import pg from 'pg';
const { Pool } = pg;

const pool = new Pool({
  connectionString: 'postgresql://postgres.llzdrxywpziewrzudwhj:eDDIYq8ottiaO9ll@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres'
});

async function check() {
  const client = await pool.connect();

  console.log('=== ROOF PROVISIONS FILTERING TEST ===\n');

  // Total Marrickville heritage Roof provisions
  const total = await client.query(`
    SELECT COUNT(*) as count
    FROM regulatory_provisions
    WHERE v2_marker = 'heritage'
      AND v2_topic = 'Roof'
      AND document_id ILIKE '%Marrickville%'
  `);
  console.log(`Total Roof provisions: ${total.rows[0].count}`);

  // By heritage type
  const byType = await client.query(`
    SELECT v2_heritage_type, COUNT(*) as count
    FROM regulatory_provisions
    WHERE v2_marker = 'heritage'
      AND v2_topic = 'Roof'
      AND document_id ILIKE '%Marrickville%'
    GROUP BY v2_heritage_type
    ORDER BY count DESC
  `);
  console.log('\nBy type:');
  byType.rows.forEach(r => {
    console.log(`  ${r.v2_heritage_type}: ${r.count}`);
  });

  // Sample controls
  console.log('\nSample CONTROL provisions (actionable):');
  const controls = await client.query(`
    SELECT id, LEFT(provision_text, 120) as text
    FROM regulatory_provisions
    WHERE v2_marker = 'heritage'
      AND v2_topic = 'Roof'
      AND v2_heritage_type = 'control'
      AND document_id ILIKE '%Marrickville%'
    LIMIT 5
  `);
  controls.rows.forEach((r, i) => {
    console.log(`\n${i+1}. ${r.text}...`);
  });

  client.release();
  await pool.end();
}

check().catch(console.error);
