import pg from 'pg';
const { Pool } = pg;
const pool = new Pool({connectionString: process.env.DATABASE_URL});

async function getTableSummary() {
  try {
    const tables = await pool.query(`
      SELECT tablename 
      FROM pg_tables 
      WHERE schemaname = 'public' 
      ORDER BY tablename
    `);
    
    console.log('=== DATABASE SUMMARY (58 tables) ===\n');
    
    for (const table of tables.rows) {
      const tableName = table.tablename;
      const count = await pool.query(`SELECT COUNT(*) as count FROM ${tableName}`);
      const columns = await pool.query(`
        SELECT COUNT(*) as count 
        FROM information_schema.columns 
        WHERE table_name = $1
      `, [tableName]);
      
      const rowCount = count.rows[0].count;
      const colCount = columns.rows[0].count;
      
      console.log(tableName.padEnd(50) + ' | ' + String(rowCount).padStart(8) + ' rows | ' + String(colCount).padStart(3) + ' cols');
    }
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await pool.end();
  }
}

getTableSummary();
