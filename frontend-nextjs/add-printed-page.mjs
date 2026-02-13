import dotenv from 'dotenv';
import pg from 'pg';
dotenv.config({ path: '.env.local' });
const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });

console.log('Adding pdf_printed_page column and calculating offsets...\n');

// Add column if not exists
await pool.query(`
  ALTER TABLE regulatory_provisions 
  ADD COLUMN IF NOT EXISTS pdf_printed_page INTEGER
`);
console.log('✅ Column added');

// For Marrickville Heritage (8.0_Heritage), offset = 14
// Extraction page 20 = Printed page 6
await pool.query(`
  UPDATE regulatory_provisions
  SET pdf_printed_page = pdf_page - 14
  WHERE document_id ILIKE '%Marrickville%'
    AND v2_marker = 'heritage'
    AND pdf_page IS NOT NULL
`);

const r = await pool.query(`
  SELECT COUNT(*) as count
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
    AND v2_marker = 'heritage'
    AND pdf_printed_page IS NOT NULL
`);

console.log(`✅ Updated ${r.rows[0].count} Marrickville heritage provisions with printed page numbers`);

// Sample check
const sample = await pool.query(`
  SELECT pdf_page, pdf_printed_page, LEFT(provision_text, 80) as text
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
    AND v2_marker = 'heritage'
    AND pdf_page IN (20, 21, 23)
  LIMIT 5
`);

console.log('\nSample verification:');
sample.rows.forEach(p => {
  console.log(`  Extraction p${p.pdf_page} → Printed p${p.pdf_printed_page} | ${p.text}...`);
});

await pool.end();
