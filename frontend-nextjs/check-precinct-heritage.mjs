import pg from 'pg';
const { Pool } = pg;

const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

async function runChecks() {
  const client = await pool.connect();

  try {
    console.log('=== CHECK 1: Provisions with v2_precinct_id = "3_" ===');
    const check1 = await client.query(`
      SELECT COUNT(*) as count
      FROM regulatory_provisions
      WHERE v2_precinct_id = '3_'
    `);
    console.log(`Count: ${check1.rows[0].count}`);

    console.log('\n=== CHECK 2: All Marrickville precinct IDs ===');
    const check2 = await client.query(`
      SELECT v2_precinct_id, COUNT(*) as count
      FROM regulatory_provisions
      WHERE document_id ILIKE '%Marrickville%'
        AND v2_dcp_layer = 'precinct'
        AND v2_precinct_id IS NOT NULL AND v2_precinct_id != ''
      GROUP BY v2_precinct_id
      ORDER BY v2_precinct_id
    `);
    console.table(check2.rows);

    console.log('\n=== CHECK 3: Stanmore-related precinct provisions ===');
    const check3 = await client.query(`
      SELECT v2_precinct_id, COUNT(*) as count,
             STRING_AGG(DISTINCT LEFT(provision_text, 60), ' | ') as sample_text
      FROM regulatory_provisions
      WHERE document_id ILIKE '%Marrickville%'
        AND v2_dcp_layer = 'precinct'
        AND (v2_precinct_id ILIKE '%3%' OR provision_text ILIKE '%stanmore%')
        AND v2_precinct_id IS NOT NULL AND v2_precinct_id != ''
      GROUP BY v2_precinct_id
      ORDER BY v2_precinct_id
      LIMIT 20
    `);
    console.table(check3.rows);

    console.log('\n=== CHECK 4: Heritage provisions with v2_heritage_element ===');
    const check4 = await client.query(`
      SELECT COUNT(*) as count
      FROM regulatory_provisions
      WHERE v2_marker = 'heritage'
        AND v2_heritage_element IS NOT NULL
    `);
    console.log(`Count with v2_heritage_element: ${check4.rows[0].count}`);

    console.log('\n=== CHECK 5: Total heritage provisions ===');
    const check5 = await client.query(`
      SELECT COUNT(*) as total_heritage
      FROM regulatory_provisions
      WHERE v2_marker = 'heritage'
    `);
    console.log(`Total heritage provisions: ${check5.rows[0].total_heritage}`);

    console.log('\n=== CHECK 6: Sample heritage provisions from Marrickville ===');
    const check6 = await client.query(`
      SELECT id, document_id, v2_heritage_type, v2_heritage_element, v2_heritage_hca,
             LEFT(provision_text, 100) as text_sample
      FROM regulatory_provisions
      WHERE v2_marker = 'heritage'
        AND document_id ILIKE '%Marrickville%'
      ORDER BY id
      LIMIT 10
    `);
    console.table(check6.rows);

    console.log('\n=== CHECK 7: Precinct layer provisions for Marrickville Part 9 ===');
    const check7 = await client.query(`
      SELECT DISTINCT v2_dcp_part, v2_precinct_id, COUNT(*) as count
      FROM regulatory_provisions
      WHERE document_id ILIKE '%Marrickville%'
        AND v2_dcp_layer = 'precinct'
      GROUP BY v2_dcp_part, v2_precinct_id
      ORDER BY v2_dcp_part, v2_precinct_id
      LIMIT 30
    `);
    console.log('Marrickville precinct provisions by Part and precinct_id:');
    console.table(check7.rows);

  } finally {
    client.release();
    await pool.end();
  }
}

runChecks().catch(console.error);
