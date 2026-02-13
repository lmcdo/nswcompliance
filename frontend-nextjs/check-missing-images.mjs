import dotenv from 'dotenv';
import pg from 'pg';
const { Pool } = pg;

dotenv.config({ path: '.env.local' });

const pool = new Pool({
  host: process.env.PGHOST,
  database: process.env.PGDATABASE,
  user: process.env.PGUSER,
  password: process.env.PGPASSWORD,
  port: parseInt(process.env.PGPORT || '5432'),
  ssl: process.env.PGHOST?.includes('supabase') ? { rejectUnauthorized: false } : undefined,
});

// Check Marrickville heritage provisions without images
const withoutImages = await pool.query(`
  SELECT COUNT(*) as count
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
    AND v2_marker = 'heritage'
    AND pdf_page_image_url IS NULL
`);

const withImages = await pool.query(`
  SELECT COUNT(*) as count
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
    AND v2_marker = 'heritage'
    AND pdf_page_image_url IS NOT NULL
`);

console.log('Marrickville Heritage Provisions:');
console.log(`  WITH images on R2: ${withImages.rows[0].count}`);
console.log(`  WITHOUT images: ${withoutImages.rows[0].count}`);
console.log(`  Total: ${parseInt(withImages.rows[0].count) + parseInt(withoutImages.rows[0].count)}`);

if (withoutImages.rows[0].count > 0) {
  const sample = await pool.query(`
    SELECT id, pdf_page, pdf_source_file, LEFT(provision_text, 100) as text
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Marrickville%'
      AND v2_marker = 'heritage'
      AND pdf_page_image_url IS NULL
    LIMIT 5
  `);
  
  console.log('\nSample provisions WITHOUT images:');
  sample.rows.forEach(p => {
    console.log(`  ID ${p.id} - Page ${p.pdf_page || 'NULL'} - ${p.pdf_source_file || 'NULL'}`);
    console.log(`    Text: ${p.text}...`);
  });
}

await pool.end();
