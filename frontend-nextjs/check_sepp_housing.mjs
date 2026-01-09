import pg from 'pg';
const { Pool } = pg;
const pool = new Pool({connectionString: process.env.DATABASE_URL});

async function checkSEPPHousing() {
  try {
    // Check sepp_structured_requirements for housing 2021
    const structured = await pool.query(`
      SELECT id, sepp_id, sepp_name, requirement_data
      FROM sepp_structured_requirements
      WHERE sepp_id ILIKE '%housing%'
      LIMIT 5
    `);
    
    console.log('=== SEPP Housing in sepp_structured_requirements ===');
    console.log('Total found:', structured.rowCount);
    structured.rows.forEach(r => {
      console.log('\n[' + r.id + '] ' + r.sepp_id + ' - ' + r.sepp_name);
      console.log('Data keys:', Object.keys(r.requirement_data || {}));
    });
    
    // Check regulatory_provisions for housing SEPP
    const reg = await pool.query(`
      SELECT COUNT(*) as count, document_id
      FROM regulatory_provisions
      WHERE document_id ILIKE '%housing%'
      GROUP BY document_id
      LIMIT 10
    `);
    
    console.log('\n\n=== SEPP Housing in regulatory_provisions ===');
    console.log('Documents found:', reg.rowCount);
    reg.rows.forEach(r => {
      console.log('  ' + r.document_id + ' (' + r.count + ' provisions)');
    });
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await pool.end();
  }
}

checkSEPPHousing();
