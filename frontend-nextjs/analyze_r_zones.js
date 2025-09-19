const { Pool } = require('pg');
const pool = new Pool({host: 'localhost', port: 5432, database: 'nsw_planning', user: 'postgres', password: 'postgres'});

async function analyzeRZones() {
  console.log('COMPREHENSIVE R-ZONE ANALYSIS');
  console.log('='.repeat(50));
  
  // Check all R zones
  const rZones = ['R1', 'R2', 'R3', 'R4', 'R5'];
  
  for (const zone of rZones) {
    console.log(`\n${zone} ZONE:`);
    console.log('-'.repeat(20));
    
    // Get basic stats
    const stats = await pool.query('SELECT COUNT(*) as provisions, COUNT(DISTINCT development_type) as dev_types FROM regulatory_provisions WHERE zone = $1', [zone]);
    console.log(`Provisions: ${stats.rows[0].provisions}, Dev types: ${stats.rows[0].dev_types}`);
    
    // Get development types
    const devTypes = await pool.query('SELECT development_type, COUNT(*) as count FROM regulatory_provisions WHERE zone = $1 AND development_type IS NOT NULL GROUP BY development_type ORDER BY count DESC', [zone]);
    console.log('Development types:');
    devTypes.rows.forEach(row => {
      console.log(`  ${row.development_type}: ${row.count}`);
    });
    
    // Get quantitative standards details
    const standards = await pool.query(`
      SELECT rp.development_type, qs.context, qs.numeric_value, rp.ref_number 
      FROM regulatory_provisions rp 
      JOIN quantitative_standards qs ON rp.id = qs.provision_id 
      WHERE rp.zone = $1 AND qs.context LIKE $2 
      ORDER BY rp.development_type, qs.context
    `, [zone, 'setback%']);
    
    console.log(`Quantitative standards (${standards.rows.length}):`);
    if (standards.rows.length === 0) {
      console.log('  NONE');
    } else {
      const grouped = {};
      standards.rows.forEach(row => {
        const key = `${row.development_type}_${row.context}`;
        if (!grouped[key]) grouped[key] = [];
        grouped[key].push(`${row.numeric_value}m (${row.ref_number})`);
      });
      
      Object.entries(grouped).forEach(([key, values]) => {
        const [devType, context] = key.split('_');
        const boundary = context.replace('setback_', '');
        console.log(`  ${devType} ${boundary}: [${values.join(', ')}]`);
      });
    }
    
    // Check C11/C12 provisions specifically
    const c11c12 = await pool.query(`
      SELECT ref_number, development_type 
      FROM regulatory_provisions 
      WHERE zone = $1 AND (ref_number LIKE $2 OR ref_number LIKE $3) 
      ORDER BY ref_number
    `, [zone, 'C11%', 'C12%']);
    
    if (c11c12.rows.length > 0) {
      console.log(`C11/C12 provisions (${c11c12.rows.length}):`);
      c11c12.rows.forEach(row => {
        console.log(`  ${row.ref_number}: ${row.development_type || 'NULL'}`);
      });
    }
  }
  
  // Summary comparison
  console.log('\nSUMMARY COMPARISON:');
  console.log('='.repeat(30));
  
  const summary = await pool.query(`
    SELECT 
      rp.zone,
      COUNT(DISTINCT rp.development_type) as dev_types,
      COUNT(qs.id) as standards,
      array_agg(DISTINCT rp.development_type) FILTER (WHERE rp.development_type IS NOT NULL) as types,
      array_agg(DISTINCT qs.context) FILTER (WHERE qs.context IS NOT NULL) as contexts
    FROM regulatory_provisions rp
    LEFT JOIN quantitative_standards qs ON rp.id = qs.provision_id AND qs.context LIKE 'setback%'
    WHERE rp.zone LIKE 'R%'
    GROUP BY rp.zone
    ORDER BY rp.zone
  `);
  
  summary.rows.forEach(row => {
    console.log(`${row.zone}: ${row.dev_types} dev types, ${row.standards || 0} standards`);
    console.log(`  Types: ${(row.types || []).join(', ')}`);
    console.log(`  Contexts: ${(row.contexts || []).join(', ')}`);
  });
  
  await pool.end();
}

analyzeRZones();