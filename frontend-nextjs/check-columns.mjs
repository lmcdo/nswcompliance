import pg from 'pg';
const { Pool } = pg;

const pool = new Pool({
  host: process.env.PGHOST || 'localhost',
  database: process.env.PGDATABASE || 'nsw_planning',
  user: process.env.PGUSER || 'postgres',
  password: process.env.PGPASSWORD,
  port: parseInt(process.env.PGPORT || '5432'),
  ssl: process.env.PGHOST?.includes('supabase') ? { rejectUnauthorized: false } : undefined,
});

const result = await pool.query(`
  SELECT column_name, data_type
  FROM information_schema.columns
  WHERE table_name = 'regulatory_provisions'
  ORDER BY ordinal_position
`);

console.log('regulatory_provisions columns:');
result.rows.forEach(row => {
  console.log(`  ${row.column_name.padEnd(40)} ${row.data_type}`);
});

await pool.end();
