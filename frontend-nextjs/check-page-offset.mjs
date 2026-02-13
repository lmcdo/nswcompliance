import dotenv from 'dotenv';
import pg from 'pg';
dotenv.config({ path: '.env.local' });
const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });

// Sample provisions from different parts of the heritage section
const r = await pool.query(`
  SELECT id, pdf_page, pdf_page_image_url, pdf_source_file,
    LEFT(provision_text, 100) as text
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
    AND v2_marker = 'heritage'
    AND pdf_page IS NOT NULL
  ORDER BY pdf_page
  LIMIT 20
`);

console.log('Marrickville Heritage PDF page mapping:\n');
console.log('Extraction Page | Image URL | Source File');
console.log('-'.repeat(100));
r.rows.forEach(p => {
  const pageMatch = p.pdf_page_image_url?.match(/page_(\d+)\./);
  const urlPage = pageMatch ? pageMatch[1] : 'N/A';
  console.log(`${p.pdf_page} | ...page_${urlPage}.png | ${p.pdf_source_file || 'NULL'}`);
});

// Check if pdf_page matches URL extraction page
const mismatch = r.rows.find(p => {
  const pageMatch = p.pdf_page_image_url?.match(/page_(\d+)\./);
  return pageMatch && parseInt(pageMatch[1]) !== p.pdf_page;
});

console.log('\n' + '='.repeat(100));
if (mismatch) {
  console.log('⚠️  MISMATCH FOUND between pdf_page column and URL page number');
} else {
  console.log('✅ pdf_page column matches URL extraction page numbers');
  console.log('\nThe offset is: extraction_page - printed_page');
  console.log('For Page 20 extraction → Page 6 printed: offset = 14');
  console.log('\nNeed to determine the offset for Marrickville Heritage section');
}

await pool.end();
