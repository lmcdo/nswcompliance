// Check PostgreSQL schema for PRP-K7
const { Pool } = require('pg');

const pool = new Pool({
 host: 'localhost',
 port: 5432,
 database: 'nsw_planning',
 user: 'postgres',
 password: 'postgres'
});

async function checkSchema() {
 try {
 console.log('Checking PostgreSQL schema...');
 
 // Check regulatory_provisions table
 const regProvColumns = await pool.query(`
 SELECT column_name, data_type, is_nullable
 FROM information_schema.columns
 WHERE table_name = 'regulatory_provisions'
 ORDER BY ordinal_position
 `);
 
 console.log('\nregulatory_provisions columns:');
 regProvColumns.rows.forEach(col => {
 console.log(` ${col.column_name} (${col.data_type}) ${col.is_nullable === 'YES' ? 'NULL' : 'NOT NULL'}`);
 });
 
 // Check quantitative_standards table
 const quantColumns = await pool.query(`
 SELECT column_name, data_type, is_nullable
 FROM information_schema.columns
 WHERE table_name = 'quantitative_standards'
 ORDER BY ordinal_position
 `);
 
 console.log('\nquantitative_standards columns:');
 quantColumns.rows.forEach(col => {
 console.log(` ${col.column_name} (${col.data_type}) ${col.is_nullable === 'YES' ? 'NULL' : 'NOT NULL'}`);
 });
 
 // Check kg_relationships table
 const kgColumns = await pool.query(`
 SELECT column_name, data_type, is_nullable
 FROM information_schema.columns
 WHERE table_name = 'kg_relationships'
 ORDER BY ordinal_position
 `);
 
 console.log('\nkg_relationships columns:');
 kgColumns.rows.forEach(col => {
 console.log(` ${col.column_name} (${col.data_type}) ${col.is_nullable === 'YES' ? 'NULL' : 'NOT NULL'}`);
 });
 
 } catch (error) {
 console.error('Schema check error:', error.message);
 } finally {
 await pool.end();
 }
}

checkSchema();