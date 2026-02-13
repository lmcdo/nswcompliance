import dotenv from 'dotenv';
import pg from 'pg';
dotenv.config({ path: '.env.local' });
const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });

// Check if column exists
const columnCheck = await pool.query(`
  SELECT column_name, data_type 
  FROM information_schema.columns 
  WHERE table_name = 'regulatory_provisions' 
    AND column_name = 'pdf_printed_page'
`);

console.log('Column exists in production:', columnCheck.rows.length > 0);
if (columnCheck.rows.length > 0) {
  console.log('  Type:', columnCheck.rows[0].data_type);
}

// Check sample data
const sample = await pool.query(`
  SELECT id, pdf_page, pdf_printed_page, v2_topic
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
    AND v2_marker = 'heritage'
    AND v2_topic = 'Roof'
  ORDER BY pdf_page
  LIMIT 3
`);

console.log('\nSample Marrickville Heritage Roof provisions:');
sample.rows.forEach(p => {
  console.log(`  ID ${p.id} | pdf_page=${p.pdf_page} | pdf_printed_page=${p.pdf_printed_page} | topic=${p.v2_topic}`);
});

await pool.end();
