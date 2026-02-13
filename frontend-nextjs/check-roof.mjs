import dotenv from 'dotenv';
import pg from 'pg';
dotenv.config({ path: '.env.local' });
const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });

// Check roof heritage provisions
const r = await pool.query(`
  SELECT id, pdf_page, pdf_page_image_url, v2_heritage_element, v2_heritage_type,
    LEFT(provision_text, 200) as text_preview, LENGTH(provision_text) as text_len
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
    AND v2_marker = 'heritage'
    AND 'roof' = ANY(v2_heritage_element)
  ORDER BY pdf_page
`);

console.log(`Roof heritage provisions: ${r.rows.length}\n`);
r.rows.forEach(p => {
  console.log(`ID ${p.id} | Page ${p.pdf_page} | ${p.text_len} chars | elements: [${p.v2_heritage_element}]`);
  console.log(`  Image: ${p.pdf_page_image_url}`);
  console.log(`  Text: ${p.text_preview}...`);
  console.log();
});

await pool.end();
