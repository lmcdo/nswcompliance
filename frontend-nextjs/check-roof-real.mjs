import dotenv from 'dotenv';
import pg from 'pg';
dotenv.config({ path: '.env.local' });
const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });

const r = await pool.query(`
  SELECT id, pdf_page, pdf_page_image_url, v2_topic, v2_heritage_type, v2_is_actionable,
    LENGTH(provision_text) as text_len, LEFT(provision_text, 200) as text
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
    AND v2_marker = 'heritage'
    AND v2_topic = 'Roof'
  ORDER BY pdf_page
`);

console.log(`Marrickville heritage provisions with v2_topic='Roof': ${r.rows.length}\n`);
r.rows.forEach(p => {
  console.log(`ID ${p.id} | Page ${p.pdf_page} | ${p.text_len} chars | actionable=${p.v2_is_actionable} | type=${p.v2_heritage_type}`);
  console.log(`  Image: ${p.pdf_page_image_url}`);
  console.log(`  Text: ${p.text}...`);
  console.log();
});

await pool.end();
