/**
 * qa-exempt-complying-tags.cjs
 *
 * QA verification for exempt/complying work-type tagging.
 * Run after tag-exempt-complying-work-types.cjs --run completes.
 *
 * Checks:
 *   1. Distribution — counts per work type vs expected ranges
 *   2. Anchor provisions — known IDs that must be tagged correctly
 *   3. Sample review — 3 provisions per work type for human eyeballing
 *   4. Null coverage — how many provisions still have null v2_topic
 *   5. Cross-check against classification log (if present)
 *
 * Usage:
 *   node qa-exempt-complying-tags.cjs
 */

'use strict';

const { Pool } = require('./frontend-nextjs/node_modules/pg');
const fs = require('fs');
const path = require('path');

require('./frontend-nextjs/node_modules/dotenv').config({
  path: path.join(__dirname, 'frontend-nextjs/.env.local'),
});

const DOC_ID = 'State_Environmental_Planning_Policy_Exempt_and_Complying_Development_Codes_2008__NSW_Legislation';

// Known-correct anchor provisions — manually verified during investigation
const ANCHORS = [
  { id: 36277, expected: 'Deck',         note: 'Subdivision 6 Balconies, decks heading' },
  { id: 36278, expected: 'Deck',         note: 'Deck specified development clause' },
  { id: 36306, expected: 'Carport',      note: 'Carport specified development clause' },
  { id: 36556, expected: 'Fence',        note: 'Subdivision 17 Fences heading' },
  { id: 36566, expected: 'Fence',        note: 'Subdivision 17A Fences for swimming pools — pool fence → Fence or Pool' },
  { id: 36688, expected: 'Pool',         note: 'Subdivision 30 Portable swimming pools heading' },
  { id: 36762, expected: 'Solar Energy', note: 'Solar energy systems specified development clause' },
];

// Expected distribution ranges (from dry-run observation + keyword analysis)
// These are soft ranges — flag if outside, not hard failures
const EXPECTED = {
  'Fence':        { min: 50,  max: 130 },
  'Deck':         { min: 80,  max: 200 },
  'Carport':      { min: 50,  max: 130 },
  'Pool':         { min: 40,  max: 120 },
  'Solar Energy': { min: 1,   max: 20  },
  'General':      { min: 300, max: 700 },
  'other_null':   { min: 500, max: 2000 }, // provisions left with null v2_topic
};

async function main() {
  const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false },
  });

  console.log('=== QA: Exempt & Complying Work-Type Tagging ===\n');

  // ── 1. Distribution ──────────────────────────────────────────────────────
  console.log('1. DISTRIBUTION');
  const { rows: dist } = await pool.query(`
    SELECT v2_topic, COUNT(*) as cnt
    FROM regulatory_provisions
    WHERE document_id = $1
    GROUP BY v2_topic
    ORDER BY cnt DESC
  `, [DOC_ID]);

  let totalTagged = 0;
  let totalNull = 0;

  dist.forEach(row => {
    const topic = row.v2_topic || '(null)';
    const cnt = parseInt(row.cnt);
    if (!row.v2_topic) { totalNull = cnt; return; }
    totalTagged += cnt;

    const exp = EXPECTED[topic];
    const flag = exp
      ? (cnt < exp.min || cnt > exp.max ? ' ⚠ OUTSIDE EXPECTED RANGE' : ' ✓')
      : ' (unexpected topic)';
    console.log(`  ${topic.padEnd(16)} ${String(cnt).padStart(5)}${flag}`);
  });

  console.log(`  ${'(null)'.padEnd(16)} ${String(totalNull).padStart(5)}`);
  console.log(`  ${'TOTAL'.padEnd(16)} ${String(totalTagged + totalNull).padStart(5)}`);

  const nullExp = EXPECTED['other_null'];
  if (totalNull < nullExp.min || totalNull > nullExp.max) {
    console.log(`  ⚠ Null count ${totalNull} outside expected range ${nullExp.min}–${nullExp.max}`);
  }

  // ── 2. Anchor provisions ─────────────────────────────────────────────────
  console.log('\n2. ANCHOR PROVISIONS (known-correct spot checks)');
  let anchorPass = 0;
  let anchorFail = 0;

  for (const anchor of ANCHORS) {
    const { rows } = await pool.query(`
      SELECT id, v2_topic, provision_text
      FROM regulatory_provisions
      WHERE id = $1
    `, [anchor.id]);

    if (rows.length === 0) {
      console.log(`  ✗ id=${anchor.id} NOT FOUND`);
      anchorFail++;
      continue;
    }

    const actual = rows[0].v2_topic;
    const text = (rows[0].provision_text || '').substring(0, 70);

    // Some anchors accept multiple valid answers (e.g. pool fence could be Fence or Pool)
    const isFlexible = anchor.note.includes('→');
    const pass = isFlexible
      ? (actual === 'Fence' || actual === 'Pool')
      : actual === anchor.expected;

    const icon = pass ? '✓' : '✗';
    const detail = pass ? actual : `got "${actual}", expected "${anchor.expected}"`;
    console.log(`  ${icon} id=${anchor.id} [${detail}] — ${text}`);
    if (pass) anchorPass++; else anchorFail++;
  }

  console.log(`  ${anchorPass}/${ANCHORS.length} anchors correct`);

  // ── 3. Sample review — 3 per work type ───────────────────────────────────
  console.log('\n3. SAMPLE REVIEW (3 per work type — human eyeball)');

  const topics = dist.filter(r => r.v2_topic).map(r => r.v2_topic);

  for (const topic of topics) {
    const { rows: samples } = await pool.query(`
      SELECT id, pdf_page, provision_text
      FROM regulatory_provisions
      WHERE document_id = $1 AND v2_topic = $2
      ORDER BY random()
      LIMIT 3
    `, [DOC_ID, topic]);

    console.log(`\n  [${topic}]`);
    samples.forEach(r => {
      console.log(`    id=${r.id} p${r.pdf_page}: ${(r.provision_text || '').substring(0, 100)}`);
    });
  }

  // ── 4. Suspicious patterns ───────────────────────────────────────────────
  console.log('\n4. SUSPICIOUS PATTERNS');

  // Check: any provisions on pages 1-26 tagged as a specific work type (should be General)
  const { rows: earlyTagged } = await pool.query(`
    SELECT v2_topic, COUNT(*) as cnt
    FROM regulatory_provisions
    WHERE document_id = $1
      AND pdf_page <= 26
      AND v2_topic NOT IN ('General', 'general')
      AND v2_topic IS NOT NULL
    GROUP BY v2_topic
    ORDER BY cnt DESC
  `, [DOC_ID]);

  if (earlyTagged.length === 0) {
    console.log('  ✓ No specific work types tagged on pages 1-26 (all correctly General)');
  } else {
    console.log('  ⚠ Work types found on pages 1-26 (expected General only):');
    earlyTagged.forEach(r => console.log(`    ${r.v2_topic}: ${r.cnt}`));
  }

  // Check: pool fence provisions — should be Pool not Fence (safety critical)
  const { rows: poolFence } = await pool.query(`
    SELECT id, v2_topic, provision_text
    FROM regulatory_provisions
    WHERE document_id = $1
      AND provision_text ILIKE '%swimming pool%'
      AND provision_text ILIKE '%fence%'
      AND v2_topic = 'Fence'
    LIMIT 5
  `, [DOC_ID]);

  if (poolFence.length === 0) {
    console.log('  ✓ No pool+fence provisions tagged as Fence only');
  } else {
    console.log(`  ⚠ ${poolFence.length} pool fence provisions tagged as Fence (consider Pool for safety):`)
    poolFence.forEach(r => console.log(`    id=${r.id}: ${(r.provision_text || '').substring(0, 80)}`));
  }

  // ── 5. Log cross-check ───────────────────────────────────────────────────
  const logPath = path.join(__dirname, 'frontend-nextjs/exempt-complying-classification-log.json');
  if (fs.existsSync(logPath)) {
    const log = JSON.parse(fs.readFileSync(logPath));
    console.log(`\n5. LOG CROSS-CHECK`);
    console.log(`  Log entries: ${log.length}`);
    const logDist = {};
    log.forEach(r => { logDist[r.work_type] = (logDist[r.work_type] || 0) + 1; });
    console.log('  Log distribution:', Object.entries(logDist).map(([k,v]) => `${k}:${v}`).join(' '));
    console.log(`  DB tagged provisions: ${totalTagged} (log has ${log.filter(r => r.work_type !== 'other').length} non-other)`);
  }

  console.log('\n=== QA complete ===');
  console.log('If all anchors pass and samples look reasonable, tagging is production-ready.');
  console.log('For any failures: re-run tagger on specific IDs or adjust prompt and re-classify.');

  await pool.end();
}

main().catch(e => { console.error('Fatal:', e); process.exit(1); });
