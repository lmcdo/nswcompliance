import pg from 'pg';
const { Pool } = pg;
const pool = new Pool({connectionString: process.env.DATABASE_URL});

async function findTODParking() {
  try {
    const result = await pool.query(`
      SELECT 
        v2_precinct_id,
        ref_number,
        v2_dcp_part,
        provision_text,
        document_id
      FROM regulatory_provisions
      WHERE document_id ILIKE '%Marrickville%'
      AND v2_precinct_id IS NOT NULL
      AND provision_text ILIKE '%parking%'
      AND (
        provision_text ILIKE '%0.5%'
        OR provision_text ILIKE '%0.75%'
        OR provision_text ILIKE '%TOD%'
        OR provision_text ILIKE '%transport%oriented%'
        OR provision_text ILIKE '%newtown%station%'
        OR provision_text ILIKE '%dulwich%station%'
      )
      ORDER BY v2_precinct_id
      LIMIT 30
    `);
    
    console.log('=== TOD Parking Provisions in Marrickville ===');
    console.log('Total found:', result.rowCount);
    console.log('');
    
    result.rows.forEach((r, i) => {
      console.log('[' + (i+1) + '] Precinct: ' + r.v2_precinct_id);
      console.log('    Ref: ' + r.ref_number);
      console.log('    Part: ' + (r.v2_dcp_part || 'N/A'));
      console.log('    Document: ' + r.document_id.substring(0, 60) + '...');
      console.log('    Text: ' + (r.provision_text || '').substring(0, 300));
      console.log('');
    });
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await pool.end();
  }
}

findTODParking();
