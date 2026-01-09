import pg from 'pg';
const { Pool } = pg;
const pool = new Pool({connectionString: process.env.DATABASE_URL});

async function checkSummerHill() {
  try {
    const result = await pool.query(`
      SELECT ref_number, section_header, provision_text
      FROM dcp_precinct_provisions
      WHERE precinct_id = 'D8'
      AND provision_text ILIKE '%parking%'
      ORDER BY display_order
    `);
    
    console.log('=== Summer Hill (D8) Parking Provisions ===');
    console.log('Total found:', result.rowCount);
    console.log('');
    
    result.rows.forEach((r, i) => {
      console.log('[' + (i+1) + '] Ref: ' + r.ref_number);
      console.log('    Section: ' + (r.section_header || 'N/A'));
      console.log('    Text: ' + (r.provision_text || '').substring(0, 400) + '...\n');
    });
    
    const todResult = await pool.query(`
      SELECT ref_number, section_header, provision_text
      FROM dcp_precinct_provisions
      WHERE precinct_id = 'D8'
      AND (provision_text ILIKE '%TOD%' OR provision_text ILIKE '%transport%oriented%')
      ORDER BY display_order
    `);
    
    console.log('\n=== Summer Hill (D8) TOD/Transport Provisions ===');
    console.log('Total found:', todResult.rowCount);
    console.log('');
    
    todResult.rows.forEach((r, i) => {
      console.log('[' + (i+1) + '] Ref: ' + r.ref_number);
      console.log('    Section: ' + (r.section_header || 'N/A'));
      console.log('    Text: ' + (r.provision_text || '').substring(0, 400) + '...\n');
    });
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await pool.end();
  }
}

checkSummerHill();
