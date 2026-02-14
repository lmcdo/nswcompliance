'use strict';

/**
 * tag-exempt-complying-parts.cjs
 *
 * Tags each SEPP E&C provision with the housing code Part it belongs to (v2_part).
 * Uses clause-number prefix first (most reliable), then page-range fallback.
 *
 * Part mapping:
 *   Part 3   Housing Code                    pages 112–155
 *   Part 3A  Rural Housing Code              pages 156–168
 *   Part 3B  Low Rise Housing Diversity Code pages 169–228
 *   Part 3C  Greenfield Housing Code         pages 229–269
 *   Part 3D  Inland Code                     pages 270+
 *   Part 2   Exempt Development Code         pages 27–111
 *   Part 1   General                         pages 1–26
 *   (null)   image placeholders / no pdf_page
 *
 * Column written: v2_part (TEXT) — must exist in regulatory_provisions.
 * Check first: SELECT column_name FROM information_schema.columns
 *              WHERE table_name='regulatory_provisions' AND column_name='v2_part';
 *
 * Usage:
 *   node tag-exempt-complying-parts.cjs          (dry run — shows distribution)
 *   node tag-exempt-complying-parts.cjs --run    (live update)
 */

const { Pool } = require('./frontend-nextjs/node_modules/pg');
const path = require('path');

require('./frontend-nextjs/node_modules/dotenv').config({
  path: path.join(__dirname, 'frontend-nextjs/.env.local'),
});

const DOC_ID = 'State_Environmental_Planning_Policy_Exempt_and_Complying_Development_Codes_2008__NSW_Legislation';
const DRY_RUN = !process.argv.includes('--run');

// Clause-number prefix → Part (checked before page range)
const CLAUSE_PREFIXES = [
  { prefix: '3D.', part: '3D' },
  { prefix: '3C.', part: '3C' },
  { prefix: '3B.', part: '3B' },
  { prefix: '3BA.', part: '3B' }, // 3BA is a sub-division of 3B
  { prefix: '3A.', part: '3A' },
  { prefix: '3.',  part: '3'  }, // must come after 3A/3B/3C/3D
  { prefix: '2.',  part: '2'  },
  { prefix: '1.',  part: '1'  },
];

// Page range → Part (fallback when no clause prefix match)
function partFromPage(page) {
  if (!page) return null;
  if (page >= 270) return '3D';
  if (page >= 229) return '3C';
  if (page >= 169) return '3B';
  if (page >= 156) return '3A';
  if (page >= 112) return '3';
  if (page >= 27)  return '2';
  return '1';
}

function classifyProvision(row) {
  const text = (row.provision_text || '').trimStart();

  // Try clause-number prefix first
  for (const { prefix, part } of CLAUSE_PREFIXES) {
    if (text.startsWith(prefix)) return part;
  }

  // Fall back to page range
  return partFromPage(row.pdf_page);
}

async function main() {
  const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false },
  });

  console.log(`Mode: ${DRY_RUN ? 'DRY RUN (--run to apply)' : 'LIVE UPDATE'}`);

  // Check v2_part column exists
  const { rows: cols } = await pool.query(
    `SELECT column_name FROM information_schema.columns
     WHERE table_name = 'regulatory_provisions' AND column_name = 'v2_part'`
  );
  if (cols.length === 0) {
    console.error('ERROR: column v2_part does not exist in regulatory_provisions.');
    console.error('Run this first:');
    console.error("  ALTER TABLE regulatory_provisions ADD COLUMN v2_part TEXT;");
    await pool.end();
    process.exit(1);
  }

  // Fetch all provisions
  const { rows } = await pool.query(
    `SELECT id, pdf_page, provision_text FROM regulatory_provisions
     WHERE document_id = $1 ORDER BY id`,
    [DOC_ID]
  );

  console.log(`Total provisions: ${rows.length}`);

  // Classify
  const results = rows.map(row => ({
    id: row.id,
    part: classifyProvision(row),
  }));

  // Distribution
  const dist = {};
  results.forEach(r => { dist[r.part || '(null)'] = (dist[r.part || '(null)'] || 0) + 1; });
  console.log('\nPart distribution:');
  Object.entries(dist).sort((a, b) => {
    const order = ['1','2','3','3A','3B','3C','3D','(null)'];
    return order.indexOf(a[0]) - order.indexOf(b[0]);
  }).forEach(([k, v]) => console.log(`  Part ${k.padEnd(5)} ${v}`));

  if (DRY_RUN) {
    console.log('\nDRY RUN — showing sample of each Part:');
    const parts = ['3', '3A', '3B', '3C', '3D'];
    for (const p of parts) {
      const sample = results.filter(r => r.part === p).slice(0, 3);
      console.log(`\n  [Part ${p}]`);
      sample.forEach(r => {
        const row = rows.find(x => x.id === r.id);
        console.log(`    id=${r.id} p${row.pdf_page}: ${(row.provision_text||'').substring(0, 90)}`);
      });
    }
    console.log('\nRun with --run to apply to database.');
    await pool.end();
    return;
  }

  // Apply to DB
  console.log('\nApplying to database...');
  let updated = 0;
  let nulled = 0;

  for (const result of results) {
    await pool.query(
      `UPDATE regulatory_provisions SET v2_part = $1 WHERE id = $2`,
      [result.part, result.id]
    );
    if (result.part) updated++;
    else nulled++;
  }

  console.log(`Updated: ${updated} provisions with v2_part`);
  if (nulled) console.log(`Nulled: ${nulled} provisions (no page, image placeholders)`);
  console.log('\nDone.');

  await pool.end();
}

main().catch(e => { console.error('Fatal:', e); process.exit(1); });
