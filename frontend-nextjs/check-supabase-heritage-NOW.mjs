import pg from 'pg';
const { Pool } = pg;

const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

async function check() {
  const client = await pool.connect();

  console.log('=== SUPABASE PRODUCTION - HERITAGE DATA STATE ===\n');

  // Check column existence
  console.log('1. CHECKING COLUMN EXISTENCE:');
  const columns = await client.query(`
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'regulatory_provisions'
      AND column_name IN ('v2_topic', 'v2_marker', 'v2_heritage_type', 'v2_heritage_element', 'v2_heritage_hca')
    ORDER BY column_name
  `);
  console.table(columns.rows);

  // Check Marrickville heritage data population
  console.log('\n2. MARRICKVILLE HERITAGE DATA POPULATION:');
  const marrickville = await client.query(`
    SELECT 
      COUNT(*) as total_heritage,
      COUNT(v2_topic) FILTER (WHERE v2_topic IS NOT NULL) as has_v2_topic,
      COUNT(v2_marker) FILTER (WHERE v2_marker IS NOT NULL) as has_v2_marker,
      COUNT(v2_heritage_type) FILTER (WHERE v2_heritage_type IS NOT NULL) as has_v2_heritage_type,
      COUNT(v2_heritage_element) FILTER (WHERE v2_heritage_element IS NOT NULL AND array_length(v2_heritage_element, 1) > 0) as has_v2_heritage_element,
      COUNT(v2_heritage_hca) FILTER (WHERE v2_heritage_hca IS NOT NULL) as has_v2_heritage_hca
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Marrickville%'
      AND (v2_marker = 'heritage' OR v2_topic ILIKE '%heritage%' OR document_id ILIKE '%Heritage%')
  `);
  console.table(marrickville.rows);

  // Check Ashfield heritage (for comparison - what's in screencast)
  console.log('\n3. ASHFIELD HERITAGE DATA POPULATION (from Feb 6 screencast):');
  const ashfield = await client.query(`
    SELECT 
      COUNT(*) as total_heritage,
      COUNT(v2_topic) FILTER (WHERE v2_topic IS NOT NULL) as has_v2_topic,
      COUNT(v2_marker) FILTER (WHERE v2_marker IS NOT NULL) as has_v2_marker,
      COUNT(v2_heritage_type) FILTER (WHERE v2_heritage_type IS NOT NULL) as has_v2_heritage_type,
      COUNT(v2_heritage_element) FILTER (WHERE v2_heritage_element IS NOT NULL AND array_length(v2_heritage_element, 1) > 0) as has_v2_heritage_element,
      COUNT(v2_heritage_hca) FILTER (WHERE v2_heritage_hca IS NOT NULL) as has_v2_heritage_hca
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Ashfield%'
      AND (v2_marker = 'heritage' OR v2_topic ILIKE '%heritage%')
  `);
  console.table(ashfield.rows);

  // Check what v2_topic values exist for heritage
  console.log('\n4. HERITAGE v2_topic VALUES (how element filtering works):');
  const topics = await client.query(`
    SELECT v2_topic, COUNT(*) as count
    FROM regulatory_provisions
    WHERE v2_marker = 'heritage'
      AND document_id ILIKE '%Marrickville%'
    GROUP BY v2_topic
    ORDER BY count DESC
    LIMIT 15
  `);
  console.table(topics.rows);

  // Sample provisions with ALL heritage fields
  console.log('\n5. SAMPLE HERITAGE PROVISIONS (showing all heritage fields):');
  const sample = await client.query(`
    SELECT 
      id,
      v2_topic,
      v2_marker,
      v2_heritage_type,
      v2_heritage_element,
      v2_heritage_hca,
      LEFT(provision_text, 80) as text_sample
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Marrickville%8.0%Heritage%'
    LIMIT 10
  `);
  console.table(sample.rows);

  client.release();
  await pool.end();
}

check().catch(console.error);
