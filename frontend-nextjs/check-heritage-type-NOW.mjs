import pg from 'pg';
const { Pool } = pg;

const pool = new Pool({
  connectionString: 'postgresql://postgres.llzdrxywpziewrzudwhj:eDDIYq8ottiaO9ll@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres'
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
