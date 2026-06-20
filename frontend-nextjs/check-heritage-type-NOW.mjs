import pg from 'pg';
const { Pool } = pg;

const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

async function check() {
  const client = await pool.connect();

  const result = await client.query(`
    SELECT
      v2_heritage_type,
      COUNT(*) as count
    FROM regulatory_provisions
    WHERE v2_marker = 'heritage'
    GROUP BY v2_heritage_type
    ORDER BY count DESC
  `);

  console.log('v2_heritage_type distribution:');
  console.table(result.rows);

  client.release();
  await pool.end();
}

check().catch(console.error);
