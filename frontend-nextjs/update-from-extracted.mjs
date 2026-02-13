import dotenv from 'dotenv';
import pg from 'pg';
import fs from 'fs';
const { Pool } = pg;

dotenv.config({ path: '.env.local' });

const pool = new Pool({
  host: process.env.PGHOST,
  database: process.env.PGDATABASE,
  user: process.env.PGUSER,
  password: process.env.PGPASSWORD,
  port: parseInt(process.env.PGPORT || '5432'),
  ssl: process.env.PGHOST?.includes('supabase') ? { rejectUnauthorized: false } : undefined,
});

console.log('Parsing already-extracted text from first run...\n');

// Read the output file from first extraction
const outputFile = 'C:\\Users\\lawre\\AppData\\Local\\Temp\\claude\\C--Users-lawre-Downloads-solvyra-projects-compliance-engine-compliance-engine\\tasks\\b86c80b.output';
const content = fs.readFileSync(outputFile, 'utf-8');

// Parse provision IDs and extracted text
const lines = content.split('\n');
const updates = [];
let currentId = null;
let inExtractedText = false;
let extractedText = '';

for (let i = 0; i < lines.length; i++) {
  const line = lines[i];
  
  // Match provision ID line: [N/549] ID 12345 - Page 67
  const idMatch = line.match(/\[(\d+)\/\d+\] ID (\d+) - Page (\d+)/);
  if (idMatch) {
    // Save previous extraction if exists
    if (currentId && extractedText) {
      updates.push({ id: currentId, text: extractedText.trim() });
    }
    currentId = parseInt(idMatch[2]);
    extractedText = '';
    inExtractedText = false;
    continue;
  }
  
  // Match successful extraction marker
  if (line.includes('✅ Extracted')) {
    inExtractedText = true;
    continue;
  }
  
  // Match "NO_SPECIFIC_PROVISION_ON_PAGE"
  if (line.includes('⚠️  No specific provision on page')) {
    if (currentId) {
      updates.push({ id: currentId, text: null, markDescriptive: true });
    }
    currentId = null;
    continue;
  }
  
  // Capture extracted text (between dashes)
  if (inExtractedText && line.includes('-'.repeat(50))) {
    if (!extractedText) {
      // Start of extracted text
      continue;
    } else {
      // End of extracted text
      inExtractedText = false;
    }
  } else if (inExtractedText && extractedText !== undefined) {
    extractedText += line.trim() + ' ';
  }
}

// Save last one
if (currentId && extractedText) {
  updates.push({ id: currentId, text: extractedText.trim() });
}

console.log(`Parsed ${updates.length} provisions from first extraction\n`);
console.log('Updating database...\n');

let updated = 0;
let markedDescriptive = 0;
let errors = 0;

for (const update of updates) {
  try {
    if (update.markDescriptive) {
      await pool.query(
        'UPDATE regulatory_provisions SET v2_is_actionable = false, v2_heritage_type = $1 WHERE id = $2',
        ['descriptive', update.id]
      );
      markedDescriptive++;
      if (markedDescriptive % 10 === 0) {
        console.log(`Marked ${markedDescriptive} as descriptive...`);
      }
    } else if (update.text) {
      await pool.query(
        'UPDATE regulatory_provisions SET provision_text = $1 WHERE id = $2',
        [update.text, update.id]
      );
      updated++;
      if (updated % 50 === 0) {
        console.log(`Updated ${updated} provisions...`);
      }
    }
  } catch (error) {
    console.error(`Error updating ID ${update.id}: ${error.message}`);
    errors++;
  }
}

console.log('\n' + '='.repeat(80));
console.log('UPDATE COMPLETE');
console.log('='.repeat(80));
console.log(`Updated: ${updated}`);
console.log(`Marked descriptive: ${markedDescriptive}`);
console.log(`Errors: ${errors}`);
console.log('='.repeat(80));

await pool.end();
