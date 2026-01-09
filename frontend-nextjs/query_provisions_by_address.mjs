import pg from 'pg';
const { Pool } = pg;
const pool = new Pool({connectionString: process.env.DATABASE_URL});

async function queryByAddress(address, lga) {
  console.log('\n=== Querying provisions for: ' + address + ' (LGA: ' + lga + ') ===\n');
  
  try {
    const result = await pool.query(`
      SELECT 
        id,
        ref_number,
        v2_dcp_part,
        v2_precinct_id,
        provision_text
      FROM regulatory_provisions
      WHERE lga ILIKE $1
      AND v2_precinct_id IS NOT NULL
      AND v2_precinct_id != ''
      ORDER BY v2_precinct_id, ref_number
      LIMIT 100
    `, ['%' + lga + '%']);
    
    console.log('Total provisions with precinct_id:', result.rowCount);
    
    if (result.rowCount === 0) {
      console.log('NO PRECINCTS FOUND\n');
      return;
    }
    
    const byPrecinct = {};
    result.rows.forEach(r => {
      if (!byPrecinct[r.v2_precinct_id]) {
        byPrecinct[r.v2_precinct_id] = [];
      }
      byPrecinct[r.v2_precinct_id].push(r);
    });
    
    console.log('Distinct precincts:', Object.keys(byPrecinct).length);
    console.log('');
    
    Object.keys(byPrecinct).forEach(precinctId => {
      console.log('Precinct: ' + precinctId + ' (' + byPrecinct[precinctId].length + ' provisions)');
      byPrecinct[precinctId].slice(0, 2).forEach(p => {
        console.log('  [' + p.ref_number + '] Part: ' + (p.v2_dcp_part || 'N/A'));
        console.log('      Text: ' + (p.provision_text || '').substring(0, 120) + '...');
      });
      console.log('');
    });
    
  } catch (error) {
    console.error('Error:', error.message);
  }
}

async function run() {
  await queryByAddress('50 Balmain Road, Leichhardt', 'Leichhardt');
  await queryByAddress('18 Sydenham Road, Marrickville', 'Marrickville');
  await queryByAddress('1 Holden Street, Ashfield', 'Ashfield');
  await pool.end();
}

run();
