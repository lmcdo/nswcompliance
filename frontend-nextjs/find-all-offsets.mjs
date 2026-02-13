import dotenv from 'dotenv';
import pg from 'pg';
dotenv.config({ path: '.env.local' });
const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });

console.log('Finding PDF page offsets for ALL councils and document types...\n');

// Get all unique document_id + pdf_source_file combinations
const docs = await pool.query(`
  SELECT DISTINCT 
    document_id,
    pdf_source_file,
    COUNT(*) as provision_count
  FROM regulatory_provisions
  WHERE pdf_page IS NOT NULL
    AND pdf_page_image_url IS NOT NULL
  GROUP BY document_id, pdf_source_file
  ORDER BY document_id, pdf_source_file
`);

console.log(`Found ${docs.rows.length} unique document sections with PDF pages:\n`);

for (const doc of docs.rows) {
  console.log(`\n${'='.repeat(100)}`);
  console.log(`Document: ${doc.document_id}`);
  console.log(`Source: ${doc.pdf_source_file || 'NULL'}`);
  console.log(`Provisions: ${doc.provision_count}`);
  console.log('-'.repeat(100));
  
  // Get sample provisions from this document
  const samples = await pool.query(`
    SELECT pdf_page, pdf_page_image_url, LEFT(provision_text, 80) as text
    FROM regulatory_provisions
    WHERE document_id = $1
      AND ($2::text IS NULL AND pdf_source_file IS NULL OR pdf_source_file = $2)
      AND pdf_page IS NOT NULL
    ORDER BY pdf_page
    LIMIT 5
  `, [doc.document_id, doc.pdf_source_file]);
  
  console.log('Sample pages (extraction page | URL):');
  samples.rows.forEach(s => {
    const urlMatch = s.pdf_page_image_url?.match(/page_(\d+)\./);
    const urlPage = urlMatch ? urlMatch[1] : 'N/A';
    console.log(`  Page ${s.pdf_page} | ...page_${urlPage}.png | ${s.text}...`);
  });
  
  // Try to detect the offset from common patterns
  const firstPage = samples.rows[0];
  if (firstPage && firstPage.provision_text) {
    // Look for patterns like "Marrickville Development Control Plan 2011  6"
    const pageNumMatch = firstPage.provision_text.match(/(?:Plan|DCP)\s+\d{4}\s+(\d+)$/m);
    if (pageNumMatch) {
      const printedPage = parseInt(pageNumMatch[1]);
      const offset = firstPage.pdf_page - printedPage;
      console.log(`  ⭐ DETECTED OFFSET: ${offset} (extraction page ${firstPage.pdf_page} - printed page ${printedPage})`);
    }
  }
}

await pool.end();
