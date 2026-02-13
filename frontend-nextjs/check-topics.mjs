import dotenv from 'dotenv';
import pg from 'pg';
dotenv.config({ path: '.env.local' });
const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });

const r = await pool.query(`
  SELECT v2_topic, COUNT(*) as count
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
    AND v2_marker = 'heritage'
  GROUP BY v2_topic
  ORDER BY count DESC
`);

console.log('Marrickville heritage v2_topic distribution:');
r.rows.forEach(t => console.log(`  ${t.v2_topic || 'NULL'}: ${t.count}`));

await pool.end();
