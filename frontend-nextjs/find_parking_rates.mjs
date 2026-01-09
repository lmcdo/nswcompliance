import pg from 'pg';
const { Pool } = pg;
const pool = new Pool({connectionString: process.env.DATABASE_URL});

async function findParkingRates() {
  try {
    // Search for provisions with specific parking rate numbers
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
      AND (
        (provision_text ILIKE '%0.5%space%' OR provision_text ILIKE '%0.5%dwelling%')
        OR (provision_text ILIKE '%0.75%space%' OR provision_text ILIKE '%0.75%dwelling%')
        OR (provision_text ILIKE '%1.0%space%' OR provision_text ILIKE '%1 space%')
        OR provision_text ~* '\d+(\.\d+)?\s*(spaces?|dwellings?)'
      )
      ORDER BY v2_precinct_id
      LIMIT 20
    `);
    
    console.log('=== Parking Rate Provisions in Marrickville ===');
    console.log('Total found:', result.rowCount);
    console.log('');
    
    if (result.rowCount === 0) {
      console.log('NO NUMERIC PARKING RATES FOUND');
    } else {
      result.rows.forEach((r, i) => {
        console.log('[' + (i+1) + '] Precinct: ' + r.v2_precinct_id);
        console.log('    Ref: ' + r.ref_number);
        console.log('    Document: ' + r.document_id.substring(0, 70));
        console.log('    Text: ' + (r.provision_text || '').substring(0, 400) + '...');
        console.log('');
      });
    }
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await pool.end();
  }
}

findParkingRates();
