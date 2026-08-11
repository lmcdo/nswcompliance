#!/usr/bin/env node
/**
 * Get list of actionable pages for a SEPP document
 *
 * Usage:
 *   node scripts/get-sepp-actionable-pages.js "Transport and Infrastructure"
 *
 * Output:
 *   JSON array of page numbers that contain actionable provisions
 */

const { Pool } = require('pg');
const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '..', '.env.local'), silent: true });

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

async function getActionablePages(seppNamePattern) {
  const query = `
    SELECT DISTINCT rp.pdf_page
    FROM regulatory_provisions rp
    JOIN documents d ON rp.document_id = d.id
    WHERE d.document_type = 'SEPP'
      AND d.pdf_name LIKE $1
      AND rp.v2_is_actionable = true
      AND rp.pdf_page IS NOT NULL
    ORDER BY rp.pdf_page
  `;

  const result = await pool.query(query, [`%${seppNamePattern}%`]);
  return result.rows.map(r => r.pdf_page);
}

async function main() {
  const seppPattern = process.argv[2];

  if (!seppPattern) {
    console.error('Usage: node get-sepp-actionable-pages.js "<SEPP name pattern>"');
    console.error('Examples:');
    console.error('  node get-sepp-actionable-pages.js "Transport and Infrastructure"');
    console.error('  node get-sepp-actionable-pages.js "Biodiversity"');
    console.error('  node get-sepp-actionable-pages.js "Housing"');
    process.exit(1);
  }

  console.error(`Fetching actionable pages for SEPP matching: "${seppPattern}"`);

  const pages = await getActionablePages(seppPattern);

  console.error(`Found ${pages.length} actionable pages`);

  // Output JSON array to stdout (can be piped to Python script)
  // No newlines or extra formatting to avoid JSON parse errors
  console.log(JSON.stringify(pages));

  await pool.end();
}

main().catch(error => {
  console.error('Error:', error);
  pool.end();
  process.exit(1);
});
