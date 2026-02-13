import dotenv from 'dotenv';
import pg from 'pg';
dotenv.config({ path: '.env.local' });
const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });

const r = await pool.query(`
  SELECT id, pdf_page, pdf_printed_page, v2_topic
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
    AND v2_marker = 'heritage'
    AND v2_topic = 'Roof'
  ORDER BY pdf_page
  LIMIT 10
`);

console.log('First 10 Roof provisions:');
r.rows.forEach(p => {
  console.log(`ID ${p.id} | pdf_page=${p.pdf_page} | pdf_printed_page=${p.pdf_printed_page || 'NULL'}`);
});

await pool.end();
