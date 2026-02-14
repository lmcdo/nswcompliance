/**
 * Step 1: Create Gold Standard Dataset
 *
 * Select 30 diverse Marrickville heritage provisions for manual tagging
 * Mix of: simple (1 element), complex (multiple), general (none), edge cases
 */

import dotenv from 'dotenv';
import pg from 'pg';
import fs from 'fs';

dotenv.config({ path: '.env.local' });
const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });

// Get diverse sample of provisions
const result = await pool.query(`
  WITH heritage_provisions AS (
    SELECT
      id,
      provision_text,
      v2_topic,
      v2_heritage_type,
      pdf_printed_page,
      LENGTH(provision_text) as text_length
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Marrickville%'
      AND v2_marker = 'heritage'
      AND v2_is_actionable = true
      AND v2_heritage_type = 'control'  -- Only actionable controls
  ),
  -- Get mix of short, medium, long provisions
  short_provisions AS (
    SELECT * FROM heritage_provisions WHERE text_length < 200 ORDER BY RANDOM() LIMIT 10
  ),
  medium_provisions AS (
    SELECT * FROM heritage_provisions WHERE text_length BETWEEN 200 AND 500 ORDER BY RANDOM() LIMIT 10
  ),
  long_provisions AS (
    SELECT * FROM heritage_provisions WHERE text_length > 500 ORDER BY RANDOM() LIMIT 10
  )
  SELECT * FROM short_provisions
  UNION ALL
  SELECT * FROM medium_provisions
  UNION ALL
  SELECT * FROM long_provisions
  ORDER BY id
`);

console.log(`Selected ${result.rows.length} provisions for gold standard\n`);

// Create gold standard file
const goldStandard = result.rows.map(p => ({
  id: p.id,
  text: p.provision_text,
  text_length: p.text_length,
  v2_topic: p.v2_topic,
  pdf_page: p.pdf_printed_page,

  // TO BE FILLED MANUALLY:
  elements: [],  // User will fill this
  notes: "",     // Any ambiguity or edge case notes
  reviewed_by: "",
  reviewed_at: ""
}));

const outputPath = './gold-standard-heritage-elements.json';
fs.writeFileSync(outputPath, JSON.stringify(goldStandard, null, 2));

console.log(`✅ Created gold standard file: ${outputPath}`);
console.log('\nNEXT STEPS:');
console.log('1. Open gold-standard-heritage-elements.json');
console.log('2. For each provision, manually fill "elements" array');
console.log('3. Available elements:');
console.log('   [roof, verandah, window, door, fence, garden, facade,');
console.log('    chimney, infill, car_parking, demolition, interior,');
console.log('    materials, setback, scale]');
console.log('4. Use [] for general provisions with no specific elements');
console.log('5. Add notes for any ambiguous cases');
console.log('6. Run 02-test-llm-prompt.mjs when done');

// Also create a readable version for review
const readableOutput = result.rows.map((p, i) =>
  `\n=== PROVISION ${i + 1} (ID: ${p.id}) ===\nPage: ${p.pdf_printed_page}\nLength: ${p.text_length} chars\nTopic: ${p.v2_topic}\n\nText:\n${p.provision_text}\n\nElements: [ ]\n`
).join('\n---\n');

fs.writeFileSync('./gold-standard-readable.txt', readableOutput);
console.log(`\n📄 Also created readable version: gold-standard-readable.txt`);

await pool.end();
