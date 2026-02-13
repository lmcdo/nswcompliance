import dotenv from 'dotenv';
import pg from 'pg';
import Anthropic from '@anthropic-ai/sdk';

dotenv.config({ path: '.env.local' });

// Standalone script - not Next.js app code
// eslint-disable-next-line no-restricted-syntax
const pool = new pg.Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.PGHOST?.includes('supabase')
    ? { rejectUnauthorized: process.env.NODE_ENV === 'production' }
    : undefined,
});

const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const R2_PUBLIC_URL = 'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev';

// Only get the truncated provisions (ending with "...")
const result = await pool.query(`
  SELECT id, pdf_page, pdf_page_image_url, v2_heritage_element, v2_heritage_type
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
    AND v2_marker = 'heritage'
    AND pdf_page_image_url IS NOT NULL
    AND provision_text LIKE '%...'
    AND LENGTH(provision_text) BETWEEN 295 AND 310
  ORDER BY id
`);

const provisions = result.rows;
console.log(`Found ${provisions.length} truncated provisions to fix\n`);

let success = 0;
let errors = 0;

for (let i = 0; i < provisions.length; i++) {
  const prov = provisions[i];
  const elements = prov.v2_heritage_element || [];

  console.log(`[${i + 1}/${provisions.length}] ID ${prov.id} - Page ${prov.pdf_page}`);

  const imageUrl = `${R2_PUBLIC_URL}${prov.pdf_page_image_url}`;

  try {
    const imageResponse = await fetch(imageUrl);
    if (!imageResponse.ok) throw new Error(`HTTP ${imageResponse.status}`);
    const imageBuffer = await imageResponse.arrayBuffer();
    const imageBase64 = Buffer.from(imageBuffer).toString('base64');

    const elementContext = elements.length > 0 ? elements.join(', ') : 'heritage';

    const message = await anthropic.messages.create({
      model: 'claude-3-haiku-20240307',
      max_tokens: 2000,
      messages: [{
        role: 'user',
        content: [
          { type: 'image', source: { type: 'base64', media_type: 'image/png', data: imageBase64 } },
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
      await pool.query(
        'UPDATE regulatory_provisions SET v2_is_actionable = false, v2_heritage_type = $1 WHERE id = $2',
        ['descriptive', prov.id]
      );
      console.log(`   → Marked as descriptive`);
    } else {
      await pool.query(
        'UPDATE regulatory_provisions SET provision_text = $1 WHERE id = $2',
        [extractedText, prov.id]
      );
      console.log(`   → Updated: ${extractedText.length} chars`);
      success++;
    }
  } catch (error) {
    console.log(`   ❌ ${error.message}`);
    errors++;
  }

  if ((i + 1) % 50 === 0) {
    console.log(`\n--- Progress: ${i + 1}/${provisions.length} | OK: ${success} | Err: ${errors} ---\n`);
  }
}

console.log(`\nDONE: ${success} updated, ${errors} errors out of ${provisions.length} truncated provisions`);
await pool.end();
