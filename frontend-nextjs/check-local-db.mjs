import pg from 'pg';
const { Pool } = pg;

const pool = new Pool({
  connectionString: 'postgresql://postgres@127.0.0.1:5432/nsw_planning'
});

async function check() {
  try {
    const client = await pool.connect();
    
    // Check if database is accessible
    const version = await client.query('SELECT version()');
    console.log('✅ Database accessible');
    console.log('PostgreSQL version:', version.rows[0].version.split('\n')[0]);
    
    // Check table structure
    const columns = await client.query(`
      SELECT column_name, data_type 
      FROM information_schema.columns 
      WHERE table_name = 'regulatory_provisions'
        AND column_name LIKE '%heritage%'
      ORDER BY column_name
    `);
    console.log('\nHeritage-related columns:');
    columns.rows.forEach(r => console.log(`  ${r.column_name}: ${r.data_type}`));
    
    // Check data freshness
    const count = await client.query(`
      SELECT COUNT(*) as total,
             COUNT(v2_heritage_type) FILTER (WHERE v2_heritage_type IS NOT NULL) as with_type,
             MAX(updated_at) as last_update
      FROM regulatory_provisions
      WHERE document_id ILIKE '%Marrickville%'
        AND v2_marker = 'heritage'
    `);
    console.log('\nMarrickville heritage data:');
    console.log(`  Total provisions: ${count.rows[0].total}`);
    console.log(`  With v2_heritage_type: ${count.rows[0].with_type}`);
    console.log(`  Last update: ${count.rows[0].last_update}`);
    
    client.release();
    await pool.end();
  } catch (e) {
    console.log('❌ Cannot connect to local database');
    console.log('Error:', e.message);
    process.exit(1);
  }
}

check();
