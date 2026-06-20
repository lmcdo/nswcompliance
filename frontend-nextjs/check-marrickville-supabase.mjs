import pg from 'pg';
const { Pool } = pg;

const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

async function check() {
  const client = await pool.connect();

  console.log('=== MARRICKVILLE HERITAGE IN SUPABASE ===\n');

  // Check 1: By v2_topic = 'Heritage'
  console.log('CHECK 1: v2_topic = \'Heritage\'');
  const check1 = await client.query(`
    SELECT COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Marrickville%'
      AND v2_topic = 'Heritage'
  `);
  console.log(`Count: ${check1.rows[0].count}\n`);

  // Check 2: By v2_marker = 'heritage'
  console.log('CHECK 2: v2_marker = \'heritage\'');
  const check2 = await client.query(`
    SELECT COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Marrickville%'
      AND v2_marker = 'heritage'
  `);
  console.log(`Count: ${check2.rows[0].count}\n`);

  // Check 3: By document_id containing 'Heritage'
  console.log('CHECK 3: document_id ILIKE \'%Heritage%\'');
  const check3 = await client.query(`
    SELECT COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Marrickville%'
      AND document_id ILIKE '%Heritage%'
  `);
  console.log(`Count: ${check3.rows[0].count}\n`);

  // Check 4: What v2_topic values exist for Marrickville heritage document?
  console.log('CHECK 4: v2_topic values in Marrickville 8.0 Heritage document');
  const check4 = await client.query(`
    SELECT v2_topic, COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Marrickville%8.0%Heritage%'
    GROUP BY v2_topic
    ORDER BY count DESC
  `);
  console.table(check4.rows);

  // Check 5: Sample provisions to see v2_heritage_element
  console.log('\nCHECK 5: Sample from Marrickville 8.0 Heritage');
  const check5 = await client.query(`
    SELECT id, v2_topic, v2_marker, v2_heritage_type, v2_heritage_element,
           LEFT(provision_text, 60) as text_sample
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Marrickville%8.0%Heritage%'
    LIMIT 10
  `);
  console.table(check5.rows);

  client.release();
  await pool.end();
}

check().catch(console.error);
