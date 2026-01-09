import pg from 'pg';
const { Pool } = pg;
const pool = new Pool({connectionString: process.env.DATABASE_URL});

async function checkParkingRates() {
  try {
    const result = await pool.query(`
      SELECT precinct_id, precinct_name, ref_number, section_header, provision_text
      FROM dcp_precinct_provisions
      WHERE lga ILIKE '%inner%west%'
      AND (
        provision_text ILIKE '%0.5%space%'
        OR provision_text ILIKE '%0.75%space%'
        OR provision_text ILIKE '%1.0%space%'
        OR provision_text ILIKE '%0.5%dwelling%'
        OR provision_text ILIKE '%0.75%dwelling%'
      )
      ORDER BY precinct_id
    `);
    
    console.log('=== Provisions with Specific Parking Rates (0.5, 0.75, 1.0) ===');
    console.log('Total found:', result.rowCount);
    console.log('');
    
    result.rows.forEach((r, i) => {
      console.log('[' + (i+1) + '] Precinct: ' + r.precinct_id + ' - ' + r.precinct_name);
      console.log('    Ref: ' + r.ref_number);
      console.log('    Section: ' + (r.section_header || 'N/A'));
      console.log('    Text: ' + (r.provision_text || '').substring(0, 400) + '...\n');
    });
    
    const partB5 = await pool.query(`
      SELECT precinct_id, precinct_name, ref_number, section_header, provision_text
      FROM dcp_precinct_provisions
      WHERE lga ILIKE '%inner%west%'
      AND (
        ref_number ILIKE '%B5%'
        OR section_header ILIKE '%B5%'
        OR section_header ILIKE '%Part B%'
        OR provision_text ILIKE '%Part B5%'
      )
      LIMIT 10
    `);
    
    console.log('\n=== Provisions Mentioning "Part B5" or "B5" ===');
    console.log('Total found:', partB5.rowCount);
    console.log('');
    
    partB5.rows.forEach((r, i) => {
      console.log('[' + (i+1) + '] Precinct: ' + r.precinct_id + ' - ' + r.precinct_name);
      console.log('    Ref: ' + r.ref_number);
      console.log('    Section: ' + (r.section_header || 'N/A'));
      console.log('    Text: ' + (r.provision_text || '').substring(0, 300) + '...\n');
    });
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await pool.end();
  }
}

checkParkingRates();
