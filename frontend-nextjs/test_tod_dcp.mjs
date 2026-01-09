import pg from 'pg';
const { Pool } = pg;
const pool = new Pool({connectionString: process.env.DATABASE_URL});
async function testTODAddress() {
  try {
    console.log('Testing: 18 Sydenham Road, Marrickville (E4, near Sydenham Station 534m)');
    console.log('LGA: Inner West\n');
    const result = await pool.query('SELECT id, ref_number, provision_text, v2_topic, v2_dcp_part FROM regulatory_provisions WHERE provision_text ILIKE ' + "'%parking%'" + ' LIMIT 20');
    console.log('Found ' + result.rowCount + ' parking provisions:\n');
    result.rows.forEach((r, i) => {
      console.log('[' + (i+1) + '] ' + (r.ref_number || 'No ref'));
      console.log('    Topic: ' + (r.v2_topic || 'null'));
      console.log('    Part: ' + (r.v2_dcp_part || 'null'));
      console.log('    Text: ' + (r.provision_text?.substring(0, 200) || '') + '...\n');
    });
    const todResult = await pool.query('SELECT id, provision_text FROM regulatory_provisions WHERE provision_text ILIKE ' + "'%parking%'" + ' AND (provision_text ILIKE ' + "'%TOD%'" + ' OR provision_text ILIKE ' + "'%transport oriented%'" + ' OR provision_text ILIKE ' + "'%accessible area%'" + ' OR provision_text ILIKE ' + "'%800%m%station%'" + ') LIMIT 10');
    console.log('\n=== TOD parking provisions: ' + todResult.rowCount + ' ===\n');
    todResult.rows.forEach((r, i) => {
      console.log('[' + (i+1) + '] ' + (r.provision_text?.substring(0, 300) || '') + '...\n');
    });
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await pool.end();
  }
}
testTODAddress();
