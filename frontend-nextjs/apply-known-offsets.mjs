import dotenv from 'dotenv';
import pg from 'pg';
dotenv.config({ path: '.env.local' });
const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });

console.log('Applying known PDF page offsets...\n');

// Known offsets (add more as we discover them)
const OFFSETS = [
  {
    pattern: '%Marrickville%',
    marker: 'heritage',
    offset: 14,
    description: 'Marrickville Heritage (Part 8)'
  },
  // Add more as discovered
];

let totalUpdated = 0;

for (const config of OFFSETS) {
  console.log(`Processing: ${config.description}`);
  console.log(`  Pattern: ${config.pattern}, Marker: ${config.marker || 'ANY'}, Offset: ${config.offset}`);
  
  let query = `
    UPDATE regulatory_provisions
    SET pdf_printed_page = pdf_page - $1
    WHERE document_id ILIKE $2
      AND pdf_page IS NOT NULL
  `;
  
  const params = [config.offset, config.pattern];
  
  if (config.marker) {
    query += ` AND v2_marker = $3`;
    params.push(config.marker);
  }
  
  const result = await pool.query(query, params);
  console.log(`  ✅ Updated ${result.rowCount} provisions\n`);
  totalUpdated += result.rowCount;
}

console.log(`Total provisions updated: ${totalUpdated}`);
console.log('\nFor all other documents, pdf_printed_page will remain NULL and UI will fallback to pdf_page.');

await pool.end();
