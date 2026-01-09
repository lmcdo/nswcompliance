import pg from 'pg';
const { Pool } = pg;
const pool = new Pool({connectionString: process.env.DATABASE_URL});

async function checkDCPTables() {
  try {
    // Find all tables with 'dcp' or 'precinct' in name
    const tables = await pool.query(`
      SELECT tablename 
      FROM pg_tables 
      WHERE schemaname = 'public' 
      AND (tablename ILIKE '%dcp%' OR tablename ILIKE '%precinct%')
      ORDER BY tablename
    `);
    
    console.log('=== Tables with DCP/Precinct ===');
    tables.rows.forEach(r => console.log('  - ' + r.tablename));
    console.log('');
    
    // Check regulatory_provisions for marrickville/leichhardt
    const reg = await pool.query(`
      SELECT COUNT(*) as count, v2_precinct_id
      FROM regulatory_provisions
      WHERE v2_precinct_id IS NOT NULL
      AND v2_precinct_id != ''
      GROUP BY v2_precinct_id
      ORDER BY v2_precinct_id
      LIMIT 50
    `);
    
    console.log('=== Precincts in regulatory_provisions ===');
    console.log('Total distinct precincts:', reg.rowCount);
    reg.rows.forEach(r => {
      console.log('  ' + r.v2_precinct_id + ' (' + r.count + ' provisions)');
    });
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await pool.end();
  }
}

checkDCPTables();
