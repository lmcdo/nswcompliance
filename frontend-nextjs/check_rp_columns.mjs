import pg from 'pg';
const { Pool } = pg;
const pool = new Pool({connectionString: process.env.DATABASE_URL});

async function checkColumns() {
  try {
    const result = await pool.query(`
      SELECT column_name, data_type 
      FROM information_schema.columns 
      WHERE table_name = 'regulatory_provisions'
      ORDER BY ordinal_position
    `);
    
    console.log('=== regulatory_provisions table columns ===\n');
    result.rows.forEach(r => {
      console.log(r.column_name + ' (' + r.data_type + ')');
    });
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await pool.end();
  }
}

checkColumns();
