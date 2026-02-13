import dotenv from 'dotenv';
import pg from 'pg';
dotenv.config({ path: '.env.local' });
const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });

const samples = [20, 238, 230, 181];

for (const page of samples) {
  const r = await pool.query(`
    SELECT id, pdf_page, pdf_printed_page, pdf_page_image_url
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Marrickville%'
      AND v2_marker = 'heritage'
      AND pdf_page = $1
    LIMIT 1
  `, [page]);
  
  if (r.rows.length > 0) {
    const p = r.rows[0];
    const offset = p.pdf_page - (p.pdf_printed_page || 0);
    console.log(`Extraction page ${p.pdf_page} → Printed page ${p.pdf_printed_page || 'NULL'} | Offset: ${offset}`);
    console.log(`  Image: ${p.pdf_page_image_url}`);
  }
}

await pool.end();
