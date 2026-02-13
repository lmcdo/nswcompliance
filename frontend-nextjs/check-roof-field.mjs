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

console.log('=== Finding "Roof" provisions ===\n');

// Check v2_heritage_element for roof
const elements = await pool.query(`
  SELECT
    id,
    v2_topic,
    v2_heritage_element,
    v2_heritage_type,
    pdf_page,
    LEFT(provision_text, 200) as text_preview
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
    AND v2_marker = 'heritage'
    AND 'roof' = ANY(v2_heritage_element)
  LIMIT 10
`);

console.log(`Found ${elements.rows.length} provisions with v2_heritage_element containing 'roof':\n`);
elements.rows.forEach((r, i) => {
  console.log(`${i + 1}. ID ${r.id} | Page ${r.pdf_page} | Topic: ${r.v2_topic}`);
  console.log(`   Elements: [${r.v2_heritage_element?.join(', ')}]`);
  console.log(`   Type: ${r.v2_heritage_type}`);
  console.log(`   Text: ${r.text_preview}...`);
  console.log();
});

// Also check provision_text containing roof
const textSearch = await pool.query(`
  SELECT
    id,
    v2_topic,
    v2_heritage_element,
    pdf_page,
    LEFT(provision_text, 200) as text_preview
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
    AND v2_marker = 'heritage'
    AND provision_text ILIKE '%roof%'
  LIMIT 5
`);

console.log(`\nAlso found ${textSearch.rowCount} provisions with text containing 'roof' (showing first 5):\n`);
textSearch.rows.forEach((r, i) => {
  console.log(`${i + 1}. ID ${r.id} | Page ${r.pdf_page} | Topic: ${r.v2_topic}`);
  console.log(`   Elements: [${r.v2_heritage_element?.join(', ') || 'none'}]`);
  console.log(`   Text: ${r.text_preview}...`);
  console.log();
});

await pool.end();
