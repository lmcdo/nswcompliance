/**
 * Check provision C12 - should be tagged with both 'roof' and 'materials'
 */

import dotenv from 'dotenv';
import pg from 'pg';

dotenv.config({ path: '.env.local' });
const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });

const result = await pool.query(`
  SELECT
    id,
    provision_text,
    v2_topic,
    v2_heritage_element,
    v2_marker,
    pdf_page,
    pdf_printed_page
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
    AND v2_marker = 'heritage'
    AND provision_text ILIKE '%C12%'
    AND provision_text ILIKE '%Alterations to alleviate%'
  LIMIT 5
`);

console.log(`Found ${result.rows.length} provisions matching C12\n`);

result.rows.forEach(p => {
  console.log(`ID: ${p.id}`);
  console.log(`v2_topic: ${p.v2_topic}`);
  console.log(`v2_heritage_element: ${JSON.stringify(p.v2_heritage_element)}`);
  console.log(`Text: ${p.provision_text.substring(0, 150)}...`);
  console.log(`\nShould have: ['roof', 'materials'] in v2_heritage_element`);
  console.log(`Currently has: ${JSON.stringify(p.v2_heritage_element)}\n`);

  if (!p.v2_heritage_element || !p.v2_heritage_element.includes('materials')) {
    console.log('❌ MISSING "materials" tag - needs enrichment\n');
  } else {
    console.log('✅ Has materials tag\n');
  }
});

await pool.end();
