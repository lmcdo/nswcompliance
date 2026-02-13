/**
 * Check what PDF resources are available for re-extraction
 */

import pg from 'pg';
const { Pool } = pg;

const pool = new Pool({
  host: process.env.PGHOST || 'localhost',
  database: process.env.PGDATABASE || 'nsw_planning',
  user: process.env.PGUSER || 'postgres',
  password: process.env.PGPASSWORD,
  port: parseInt(process.env.PGPORT || '5432'),
  ssl: process.env.PGHOST?.includes('supabase') ? { rejectUnauthorized: false } : undefined,
});

console.log('Checking PDF resources for Marrickville heritage provisions...\n');

// Check sample provisions to see what PDF info we have
const sample = await pool.query(`
  SELECT
    id,
    pdf_page,
    pdf_source_file,
    pdf_page_image_url,
    document_id
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
    AND v2_marker = 'heritage'
    AND pdf_page IS NOT NULL
  LIMIT 10
`);

console.log('Sample provisions with PDF info:\n');
sample.rows.forEach((p, i) => {
  console.log(`${i + 1}. ID ${p.id} - Page ${p.pdf_page}`);
  console.log(`   Document: ${p.document_id}`);
  console.log(`   Source file: ${p.pdf_source_file || 'NULL'}`);
  console.log(`   Image URL: ${p.pdf_page_image_url || 'NULL'}`);
  console.log();
});

// Get unique source files
const sources = await pool.query(`
  SELECT DISTINCT
    pdf_source_file,
    COUNT(*) as provision_count
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
    AND v2_marker = 'heritage'
  GROUP BY pdf_source_file
  ORDER BY provision_count DESC
`);

console.log('PDF source files:\n');
sources.rows.forEach(s => {
  console.log(`  ${s.pdf_source_file || 'NULL'}: ${s.provision_count} provisions`);
});

// Check if image URLs are accessible
console.log('\nChecking if PDF page images are accessible...\n');

const withImages = await pool.query(`
  SELECT COUNT(*) as count
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
    AND v2_marker = 'heritage'
    AND pdf_page_image_url IS NOT NULL
`);

const withoutImages = await pool.query(`
  SELECT COUNT(*) as count
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
    AND v2_marker = 'heritage'
    AND pdf_page_image_url IS NULL
`);

console.log(`Provisions WITH image URLs: ${withImages.rows[0].count}`);
console.log(`Provisions WITHOUT image URLs: ${withoutImages.rows[0].count}`);

if (sample.rows[0]?.pdf_page_image_url) {
  console.log(`\nExample image URL: ${sample.rows[0].pdf_page_image_url}`);
}

await pool.end();
