import pg from 'pg';
const { Pool } = pg;

// Check LOCAL database (where tagging was done)
const localPool = new Pool({
  connectionString: 'postgresql://postgres:Onlyme123!@127.0.0.1:5432/nsw_planning'
});

// Check SUPABASE (production)
const supabasePool = new Pool({
  connectionString: 'postgresql://postgres.llzdrxywpziewrzudwhj:eDDIYq8ottiaO9ll@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres'
});

async function checkBothDatabases() {
  console.log('=== CHECKING BOTH DATABASES ===\n');

  // Check local
  console.log('LOCAL DATABASE (where tagging was done):');
  try {
    const localClient = await localPool.connect();
    const result = await localClient.query(`
      SELECT COUNT(*) as total,
             COUNT(v2_heritage_element) FILTER (WHERE v2_heritage_element IS NOT NULL AND array_length(v2_heritage_element, 1) > 0) as with_element,
             COUNT(v2_heritage_type) FILTER (WHERE v2_heritage_type IS NOT NULL) as with_type,
             COUNT(v2_heritage_hca) FILTER (WHERE v2_heritage_hca IS NOT NULL) as with_hca
      FROM regulatory_provisions
      WHERE document_id ILIKE '%Marrickville%'
        AND v2_topic = 'Heritage'
    `);
    console.log('Marrickville heritage provisions:');
    console.log(`  Total: ${result.rows[0].total}`);
    console.log(`  With v2_heritage_element: ${result.rows[0].with_element}`);
    console.log(`  With v2_heritage_type: ${result.rows[0].with_type}`);
    console.log(`  With v2_heritage_hca: ${result.rows[0].with_hca}`);

    // Sample
    const sample = await localClient.query(`
      SELECT id, v2_heritage_type, v2_heritage_element, v2_heritage_hca,
             LEFT(provision_text, 80) as text_sample
      FROM regulatory_provisions
      WHERE document_id ILIKE '%Marrickville%'
        AND v2_topic = 'Heritage'
        AND v2_heritage_element IS NOT NULL
      LIMIT 5
    `);
    console.log('\nSample tagged provisions:');
    console.table(sample.rows);

    localClient.release();
  } catch (e) {
    console.log(`ERROR: ${e.message}`);
  }

  console.log('\n---\n');

  // Check Supabase
  console.log('SUPABASE (production - what API uses):');
  try {
    const supaClient = await supabasePool.connect();
    const result = await supaClient.query(`
      SELECT COUNT(*) as total,
             COUNT(v2_heritage_element) FILTER (WHERE v2_heritage_element IS NOT NULL AND array_length(v2_heritage_element, 1) > 0) as with_element,
             COUNT(v2_heritage_type) FILTER (WHERE v2_heritage_type IS NOT NULL) as with_type,
             COUNT(v2_heritage_hca) FILTER (WHERE v2_heritage_hca IS NOT NULL) as with_hca
      FROM regulatory_provisions
      WHERE document_id ILIKE '%Marrickville%'
        AND v2_topic = 'Heritage'
    `);
    console.log('Marrickville heritage provisions:');
    console.log(`  Total: ${result.rows[0].total}`);
    console.log(`  With v2_heritage_element: ${result.rows[0].with_element}`);
    console.log(`  With v2_heritage_type: ${result.rows[0].with_type}`);
    console.log(`  With v2_heritage_hca: ${result.rows[0].with_hca}`);

    supaClient.release();
  } catch (e) {
    console.log(`ERROR: ${e.message}`);
  }

  await localPool.end();
  await supabasePool.end();
}

checkBothDatabases().catch(console.error);
