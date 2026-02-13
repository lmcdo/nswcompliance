/**
 * Test re-extraction of 10 Marrickville heritage provisions
 * Fetches from R2, uses Claude vision, shows results WITHOUT updating DB
 */

import dotenv from 'dotenv';
import pg from 'pg';
import Anthropic from '@anthropic-ai/sdk';
const { Pool } = pg;

// Load .env.local explicitly
dotenv.config({ path: '.env.local' });

const pool = new Pool({
  host: process.env.PGHOST || 'localhost',
  database: process.env.PGDATABASE || 'nsw_planning',
  user: process.env.PGUSER || 'postgres',
  password: process.env.PGPASSWORD,
  port: parseInt(process.env.PGPORT || '5432'),
  ssl: process.env.PGHOST?.includes('supabase') ? { rejectUnauthorized: false } : undefined,
});

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

const R2_PUBLIC_URL = 'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev';
const TEST_MODE = false; // FULL RUN - WILL UPDATE DATABASE
const TEST_LIMIT = 10;

console.log('='.repeat(100));
console.log('MARRICKVILLE HERITAGE RE-EXTRACTION - FULL RUN');
console.log('⚠️  THIS WILL UPDATE THE DATABASE');
console.log('='.repeat(100));
console.log();

// Get all Marrickville heritage provisions
const query = `
  SELECT
    id,
    pdf_page,
    pdf_page_image_url,
    v2_heritage_element,
    v2_heritage_type,
    LEFT(provision_text, 200) as current_text_preview
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
    AND v2_marker = 'heritage'
    AND pdf_page_image_url IS NOT NULL
  ORDER BY id
  ${TEST_MODE ? 'LIMIT $1' : ''}
`;

const result = TEST_MODE
  ? await pool.query(query, [TEST_LIMIT])
  : await pool.query(query);

const provisions = result.rows;
console.log(`Found ${provisions.length} provisions to test\n`);

let success = 0;
let errors = 0;
let skipped = 0;

for (let i = 0; i < provisions.length; i++) {
  const prov = provisions[i];
  const elements = prov.v2_heritage_element || [];

  console.log(`\n[${ i + 1}/${provisions.length}] ID ${prov.id} - Page ${prov.pdf_page}`);
  console.log(`   Elements: [${elements.join(', ')}]`);
  console.log(`   Type: ${prov.v2_heritage_type}`);
  console.log(`   Current text: ${prov.current_text_preview}...`);

  // Build full R2 URL
  const imageUrl = `${R2_PUBLIC_URL}${prov.pdf_page_image_url}`;
  console.log(`   Fetching: ${imageUrl.substring(0, 80)}...`);

  try {
    // Fetch image from R2
    const imageResponse = await fetch(imageUrl);
    if (!imageResponse.ok) {
      throw new Error(`HTTP ${imageResponse.status}`);
    }
    const imageBuffer = await imageResponse.arrayBuffer();
    const imageBase64 = Buffer.from(imageBuffer).toString('base64');

    // Extract text using Claude vision
    const elementContext = elements.length > 0 ? elements.join(', ') : 'heritage';

    const message = await anthropic.messages.create({
      model: 'claude-3-haiku-20240307',
      max_tokens: 2000,
      messages: [{
        role: 'user',
        content: [
          {
            type: 'image',
            source: {
              type: 'base64',
              media_type: 'image/png',
              data: imageBase64,
            },
          },
          {
            type: 'text',
            text: `Extract the SPECIFIC heritage provision control text from this DCP page.

CONTEXT: This provision relates to ${elementContext} in heritage areas/items.

CRITICAL RULES:
1. Extract ONLY the provision control text - NOT section headers, page headers, or intro paragraphs
2. DO NOT extract:
   - Section headers like "8.1.7 Heritage Items"
   - Page headers like "PART 8: HERITAGE"
   - Intro text like "Heritage items are listed in Schedule 5..."
   - Generic controls that apply to "all development"
3. DO extract:
   - Specific controls related to ${elementContext}
   - Provisions with "C" numbers (C1, C2, etc.) or subsection numbers (8.1.7.3, etc.)
   - Text that gives specific requirements for ${elementContext}

If this page contains MULTIPLE provisions related to ${elementContext}, extract ALL of them separated by double newlines.

If this page contains NO specific controls (only intro/header text), respond with: "NO_SPECIFIC_PROVISION_ON_PAGE"

Output the extracted provision text ONLY, with no commentary.`,
          },
        ],
      }],
    });

    const extractedText = message.content[0].text.trim();

    if (extractedText === 'NO_SPECIFIC_PROVISION_ON_PAGE') {
      console.log(`   ⚠️  No specific provision on page`);
      if (!TEST_MODE) {
        // Update to mark as descriptive/non-actionable
        await pool.query(
          'UPDATE regulatory_provisions SET v2_is_actionable = false, v2_heritage_type = $1 WHERE id = $2',
          ['descriptive', prov.id]
        );
        console.log(`      → Marked as descriptive in database`);
      }
      skipped++;
    } else {
      console.log(`   ✅ Extracted ${extractedText.length} chars:`);
      console.log(`   ${'-'.repeat(100)}`);
      console.log(`   ${extractedText.substring(0, 300)}${extractedText.length > 300 ? '...' : ''}`);
      console.log(`   ${'-'.repeat(100)}`);

      if (!TEST_MODE) {
        // Update provision_text in database
        await pool.query(
          'UPDATE regulatory_provisions SET provision_text = $1 WHERE id = $2',
          [extractedText, prov.id]
        );
        console.log(`      → Updated in database`);
      } else {
        console.log(`      → [TEST MODE: Not updating database]`);
      }

      success++;
    }

  } catch (error) {
    console.log(`   ❌ Error: ${error.message}`);
    errors++;
  }

  // Progress update every 50
  if ((i + 1) % 50 === 0) {
    console.log(`\n--- Progress: ${i + 1}/${provisions.length} ---`);
    console.log(`    Success: ${success}, Skipped: ${skipped}, Errors: ${errors}\n`);
  }
}

console.log('\n' + '='.repeat(100));
console.log(TEST_MODE ? 'TEST SUMMARY' : 'EXTRACTION COMPLETE');
console.log('='.repeat(100));
console.log(`Total processed: ${provisions.length}`);
console.log(`Successful extractions: ${success}`);
console.log(`Skipped (no controls on page): ${skipped}`);
console.log(`Errors: ${errors}`);
console.log();
if (TEST_MODE) {
  console.log('✅ Test complete - NO database changes made');
  console.log('   To run full re-extraction, set TEST_MODE = false in the script');
} else {
  console.log('✅ Database updated successfully');
  console.log(`   ${success} provisions updated with new text`);
  console.log(`   ${skipped} provisions marked as non-actionable`);
}

await pool.end();
