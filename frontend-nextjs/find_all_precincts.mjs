import pg from 'pg';
const { Pool } = pg;
const pool = new Pool({connectionString: process.env.DATABASE_URL});

async function findAllPrecincts() {
  try {
    // Get ALL distinct precincts
    const all = await pool.query(`
      SELECT DISTINCT precinct_id, precinct_name, lga
      FROM dcp_precinct_provisions
      ORDER BY lga, precinct_id
    `);
    
    console.log('=== ALL Precincts in Database ===');
    console.log('Total:', all.rowCount);
    console.log('');
    
    const byLGA = {};
    all.rows.forEach(r => {
      if (!byLGA[r.lga]) byLGA[r.lga] = [];
      byLGA[r.lga].push(r.precinct_id + ': ' + r.precinct_name);
    });
    
    Object.keys(byLGA).forEach(lga => {
      console.log(lga + ' (' + byLGA[lga].length + ' precincts)');
      byLGA[lga].forEach(p => console.log('  - ' + p));
      console.log('');
    });
    
    // Search for Marrickville and Leichhardt specifically
    const search = await pool.query(`
      SELECT DISTINCT precinct_id, precinct_name, lga
      FROM dcp_precinct_provisions
      WHERE lga ILIKE '%marrick%' OR lga ILIKE '%leichhardt%' OR precinct_name ILIKE '%marrick%' OR precinct_name ILIKE '%leichhardt%'
      ORDER BY lga, precinct_id
    `);
    
    console.log('\n=== Marrickville & Leichhardt Precincts ===');
    console.log('Total found:', search.rowCount);
    search.rows.forEach(r => {
      console.log('  ' + r.precinct_id + ': ' + r.precinct_name + ' (LGA: ' + r.lga + ')');
    });
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await pool.end();
  }
}

findAllPrecincts();
