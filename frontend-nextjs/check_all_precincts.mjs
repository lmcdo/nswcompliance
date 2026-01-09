import pg from 'pg';
const { Pool } = pg;
const pool = new Pool({connectionString: process.env.DATABASE_URL});

async function checkAllPrecincts() {
  try {
    const result = await pool.query(`
      SELECT DISTINCT precinct_id, precinct_name, lga
      FROM dcp_precinct_provisions
      WHERE lga ILIKE '%inner%west%'
      ORDER BY precinct_id
    `);
    
    console.log('=== All Inner West Precincts in Database ===');
    console.log('Total precincts:', result.rowCount);
    console.log('');
    
    result.rows.forEach((r, i) => {
      console.log('[' + (i+1) + '] ' + r.precinct_id + ': ' + r.precinct_name + ' (LGA: ' + r.lga + ')');
    });
    
    console.log('\n=== Checking for Newtown, Dulwich Hill, Summer Hill ===');
    
    const checkResult = await pool.query(`
      SELECT precinct_id, precinct_name
      FROM dcp_precinct_provisions
      WHERE precinct_name ILIKE '%newtown%' OR precinct_name ILIKE '%dulwich%' OR precinct_name ILIKE '%summer%'
      GROUP BY precinct_id, precinct_name
    `);
    
    console.log('Found:', checkResult.rowCount);
    checkResult.rows.forEach(r => {
      console.log('  - ' + r.precinct_id + ': ' + r.precinct_name);
    });
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await pool.end();
  }
}

checkAllPrecincts();
