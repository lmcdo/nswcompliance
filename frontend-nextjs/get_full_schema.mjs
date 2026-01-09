import pg from 'pg';
const { Pool } = pg;
const pool = new Pool({connectionString: process.env.DATABASE_URL});

async function getFullSchema() {
  try {
    // Get ALL tables
    const tables = await pool.query(`
      SELECT tablename 
      FROM pg_tables 
      WHERE schemaname = 'public' 
      ORDER BY tablename
    `);
    
    console.log('=== ALL TABLES (' + tables.rowCount + ') ===\n');
    
    for (const table of tables.rows) {
      const tableName = table.tablename;
      
      // Get row count
      const count = await pool.query(`SELECT COUNT(*) as count FROM ${tableName}`);
      
      // Get columns
      const columns = await pool.query(`
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_name = $1
        ORDER BY ordinal_position
      `, [tableName]);
      
      console.log('## ' + tableName);
      console.log('Rows: ' + count.rows[0].count);
      console.log('Columns (' + columns.rowCount + '):');
      
      columns.rows.forEach(col => {
        const nullable = col.is_nullable === 'YES' ? 'NULL' : 'NOT NULL';
        const def = col.column_default ? ' DEFAULT ' + col.column_default : '';
        console.log('  - ' + col.column_name + ' (' + col.data_type + ') ' + nullable + def);
      });
      
      console.log('');
    }
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await pool.end();
  }
}

getFullSchema();
