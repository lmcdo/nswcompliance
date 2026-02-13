import dotenv from 'dotenv';
import pg from 'pg';
dotenv.config({ path: '.env.local' });
const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });

// Check what heritage columns exist
const r = await pool.query(`
  SELECT column_name, data_type 
  FROM information_schema.columns 
  WHERE table_name = 'regulatory_provisions' 
    AND column_name LIKE '%heritage%'
  ORDER BY column_name
`);
console.log('Heritage columns in regulatory_provisions:');
r.rows.forEach(c => console.log(`  ${c.column_name}: ${c.data_type}`));

// Check sample heritage provision with "roof"
const sample = await pool.query(`
  SELECT id, pdf_page, v2_marker, v2_topic, v2_heritage_type, v2_heritage_element, v2_heritage_hca,
    LEFT(provision_text, 150) as text
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
    AND v2_marker = 'heritage'
  ORDER BY id
  LIMIT 20
`);

console.log('\nSample Marrickville heritage provisions:');
sample.rows.forEach(p => {
  console.log(`\nID ${p.id} | Page ${p.pdf_page} | marker=${p.v2_marker}`);
  console.log(`  topic: ${p.v2_topic}`);
  console.log(`  type: ${p.v2_heritage_type}`);
  console.log(`  element: ${JSON.stringify(p.v2_heritage_element)}`);
  console.log(`  hca: ${p.v2_heritage_hca}`);
  console.log(`  text: ${p.text}...`);
});

await pool.end();
