import pg from 'pg';
const { Pool } = pg;
const pool = new Pool({connectionString: process.env.DATABASE_URL});

async function checkB5() {
  try {
    const result = await pool.query(`
      SELECT id, ref_number, v2_dcp_part, v2_precinct_id, provision_text
      FROM regulatory_provisions
      WHERE (v2_dcp_part ILIKE '%B5%' OR v2_dcp_part ILIKE '%Part B%')
      AND provision_text ILIKE '%parking%'
      ORDER BY v2_dcp_part, ref_number
      LIMIT 20
    `);
    
    console.log('Part B5 parking provisions found:', result.rowCount);
    result.rows.forEach((r, i) => {
      console.log('[' + (i+1) + '] Part: ' + r.v2_dcp_part + ' | Precinct: ' + (r.v2_precinct_id || 'null'));
      console.log('    Text: ' + (r.provision_text?.substring(0, 250) || '') + '...\n');
    });
    
    console.log('\n=== Checking for Newtown/Dulwich Hill/Summer Hill precinct parking ===\n');
    
    const precinctResult = await pool.query(`
      SELECT id, v2_precinct_id, v2_dcp_part, provision_text
      FROM regulatory_provisions
      WHERE provision_text ILIKE '%parking%'
      AND (
        v2_precinct_id ILIKE '%newtown%' 
        OR v2_precinct_id ILIKE '%dulwich%'
        OR v2_precinct_id ILIKE '%summer%'
        OR provision_text ILIKE '%newtown%station%'
        OR provision_text ILIKE '%0.5%spaces%'
        OR provision_text ILIKE '%0.75%dwel%'
      )
      LIMIT 20
    `);
    
    console.log('Precinct-specific parking found:', precinctResult.rowCount);
    precinctResult.rows.forEach((r, i) => {
      console.log('[' + (i+1) + '] Precinct: ' + (r.v2_precinct_id || 'null') + ' | Part: ' + (r.v2_dcp_part || 'null'));
      console.log('    Text: ' + (r.provision_text?.substring(0, 300) || '') + '...\n');
    });
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await pool.end();
  }
}

checkB5();
