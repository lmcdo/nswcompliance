// Quick check of PostgreSQL zones for PRP-K7
const { Pool } = require('pg');

const pool = new Pool({
  host: 'localhost',
  port: 5432,
  database: 'nsw_planning',
  user: 'postgres',
  password: 'postgres'
});

async function checkZones() {
  try {
    console.log('Checking PostgreSQL database for PRP-K7 zones...');
    
    // Check zones
    const zoneResult = await pool.query(`
      SELECT zone, 
             COUNT(*) as provisions, 
             COUNT(DISTINCT development_type) as dev_types,
             array_agg(DISTINCT development_type) FILTER (WHERE development_type IS NOT NULL) as types
      FROM regulatory_provisions 
      WHERE zone IS NOT NULL 
      GROUP BY zone 
      ORDER BY zone
    `);
    
    console.log('\nZone Distribution:');
    console.log('-'.repeat(80));
    zoneResult.rows.forEach(row => {
      const types = row.types ? row.types.join(', ') : 'none';
      console.log(`${row.zone.padEnd(6)} | ${row.provisions.toString().padStart(4)} provisions | ${row.dev_types.toString().padStart(2)} dev types | ${types}`);
    });
    
    // Check quantitative standards linkage
    const standardsResult = await pool.query(`
      SELECT rp.zone,
             COUNT(DISTINCT rp.development_type) as dev_types,
             COUNT(qs.id) as standards
      FROM regulatory_provisions rp
      JOIN quantitative_standards qs ON rp.id = qs.provision_id
      WHERE rp.zone IN ('R1', 'R2', 'R3', 'R4')
      AND qs.context LIKE 'setback%'
      GROUP BY rp.zone
      ORDER BY rp.zone
    `);
    
    console.log('\nQuantitative Standards Linkage:');
    console.log('-'.repeat(50));
    standardsResult.rows.forEach(row => {
      console.log(`${row.zone} | ${row.dev_types} dev types | ${row.standards} standards`);
    });
    
    // Check C11/C12 provisions
    const c11c12Result = await pool.query(`
      SELECT ref_number, development_type, zone
      FROM regulatory_provisions
      WHERE ref_number LIKE 'C11%' OR ref_number LIKE 'C12%'
      ORDER BY ref_number
    `);
    
    console.log('\nC11/C12 Provisions:');
    console.log('-'.repeat(50));
    c11c12Result.rows.forEach(row => {
      console.log(`${row.ref_number} | ${row.development_type || 'null'} | ${row.zone || 'null'}`);
    });
    
  } catch (error) {
    console.error('Database error:', error.message);
  } finally {
    await pool.end();
  }
}

checkZones();