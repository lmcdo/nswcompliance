import dotenv from 'dotenv';
import pg from 'pg';
dotenv.config({ path: '.env.local' });
const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });

const r = await pool.query(`
  SELECT id, v2_heritage_hca, v2_topic, LEFT(provision_text, 60) as text
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
    AND v2_marker = 'heritage'
    AND v2_topic = 'Roof'
  LIMIT 5
`);

console.log('Roof provisions HCA values:');
r.rows.forEach(p => {
  console.log(`ID ${p.id} | hca=${p.v2_heritage_hca || 'NULL'} | ${p.text}...`);
});

await pool.end();
