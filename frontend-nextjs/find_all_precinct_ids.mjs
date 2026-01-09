import pg from 'pg';
const { Pool } = pg;
const pool = new Pool({connectionString: process.env.DATABASE_URL});

async function findAllPrecincts() {
  try {
    const result = await pool.query(`
      SELECT 
        v2_precinct_id,
        COUNT(*) as provision_count,
        MIN(document_id) as sample_document_id,
        MIN(v2_dcp_part) as sample_dcp_part
      FROM regulatory_provisions
      WHERE v2_precinct_id IS NOT NULL
      AND v2_precinct_id != ''
      GROUP BY v2_precinct_id
      ORDER BY v2_precinct_id
    `);
    
    console.log('=== ALL Precincts in regulatory_provisions ===');
    console.log('Total distinct precincts:', result.rowCount);
    console.log('');
    
    result.rows.forEach((r, i) => {
      console.log('[' + (i+1) + '] ' + r.v2_precinct_id);
      console.log('     Provisions: ' + r.provision_count);
      console.log('     Document: ' + r.sample_document_id);
      console.log('     Sample part: ' + (r.sample_dcp_part || 'N/A'));
      console.log('');
    });
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await pool.end();
  }
}

findAllPrecincts();
