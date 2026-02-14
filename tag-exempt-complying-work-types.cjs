/**
 * tag-exempt-complying-work-types.cjs
 *
 * LLM-assisted topic tagging for SEPP Exempt and Complying Development Codes 2008.
 * Classifies each provision by primary work type using claude-haiku-4-5.
 *
 * Classification layer only — provision text is never modified.
 * Human review recommended before marking complete.
 *
 * Usage:
 *   node tag-exempt-complying-work-types.cjs            (dry run — prints sample)
 *   node tag-exempt-complying-work-types.cjs --run      (live update)
 *   node tag-exempt-complying-work-types.cjs --run --batch 50  (smaller batches)
 */

'use strict';

const { Pool } = require('./frontend-nextjs/node_modules/pg');
const Anthropic = require('./frontend-nextjs/node_modules/@anthropic-ai/sdk');
const fs = require('fs');
const path = require('path');

// ─── Config ──────────────────────────────────────────────────────────────────

require('./frontend-nextjs/node_modules/dotenv').config({
  path: path.join(__dirname, 'frontend-nextjs/.env.local'),
});

const DB_URL = process.env.DATABASE_URL;
const ANTHROPIC_KEY = process.env.ANTHROPIC_API_KEY;
const DOC_ID = 'State_Environmental_Planning_Policy_Exempt_and_Complying_Development_Codes_2008__NSW_Legislation';

const DRY_RUN = !process.argv.includes('--run');
const BATCH_SIZE = (() => {
  const i = process.argv.indexOf('--batch');
  return i !== -1 ? parseInt(process.argv[i + 1], 10) : 80;
})();
const FROM_OFFSET = (() => {
  const i = process.argv.indexOf('--from-offset');
  return i !== -1 ? parseInt(process.argv[i + 1], 10) : 0;
})();

// ─── Work type definitions ────────────────────────────────────────────────────

const WORK_TYPES = [
  'fence',          // Fences and fencing — all zone types, including pool fences
  'deck',           // Balconies, decks, patios, pergolas, terraces, verandahs
  'carport',        // Carports and garages
  'pool',           // Swimming pools, spa pools, portable pools, child-resistant barriers
  'solar_energy',   // Solar energy systems, photovoltaic, small wind turbines
  'general',        // Part 1 general requirements, definitions, scope, interpretation
  'other',          // Any other specific work type (sheds, aerials, awnings, BBQs, etc.)
];

// ─── Prompt ───────────────────────────────────────────────────────────────────

function buildPrompt(provisions) {
  const items = provisions
    .map((p, i) => `[${i}] id=${p.id}\n${(p.provision_text || '').substring(0, 400)}`)
    .join('\n\n');

  return `You are classifying provisions from the NSW SEPP Exempt and Complying Development Codes 2008.

For each provision below, return the single best work_type from this list:
- fence       → fences, fencing, boundary fences, pool fences
- deck        → balconies, decks, patios, pergolas, terraces, verandahs, screen enclosures of these
- carport     → carports, garages, car parking spaces as structures
- pool        → swimming pools, spa pools, portable pools, child-resistant barriers
- solar_energy → solar energy systems, photovoltaic systems, small wind turbines
- general     → Part 1 general requirements, definitions, interpretation, scope clauses, administrative provisions
- other       → any other specific work type (sheds, aerials, skylights, clotheslines, BBQs, signage, etc.)

Rules:
- If a provision governs a pool fence specifically, classify as "pool" (safety-critical, belongs with pool results)
- If a provision lists multiple work types in a general scope clause (e.g. "the following development is specified..."), classify as "general"
- Pick the most specific and primary work type
- Return ONLY a JSON array, no other text, in this exact format:
[{"id": 36277, "work_type": "deck"}, {"id": 36278, "work_type": "deck"}, ...]

Provisions:
${items}`;
}

// ─── Main ─────────────────────────────────────────────────────────────────────

async function main() {
  const pool = new Pool({
    connectionString: DB_URL,
    ssl: { rejectUnauthorized: false },
  });

  const client = new Anthropic.default({ apiKey: ANTHROPIC_KEY });

  console.log(`Mode: ${DRY_RUN ? 'DRY RUN (--run to apply)' : 'LIVE UPDATE'}`);
  console.log(`Batch size: ${BATCH_SIZE}`);

  // Fetch all provisions for this document
  const { rows } = await pool.query(
    `SELECT id, pdf_page, provision_text
     FROM regulatory_provisions
     WHERE document_id = $1
     ORDER BY id
     OFFSET $2`,
    [DOC_ID, FROM_OFFSET]
  );

  if (FROM_OFFSET > 0) console.log(`Resuming from offset ${FROM_OFFSET} (skipping first ${FROM_OFFSET} provisions)`);

  console.log(`Total provisions: ${rows.length}`);

  // Split into batches
  const batches = [];
  for (let i = 0; i < rows.length; i += BATCH_SIZE) {
    batches.push(rows.slice(i, i + BATCH_SIZE));
  }

  console.log(`Batches: ${batches.length}`);

  const results = [];
  let errors = 0;

  for (let b = 0; b < batches.length; b++) {
    const batch = batches[b];
    const start = b * BATCH_SIZE + 1;
    const end = start + batch.length - 1;
    process.stdout.write(`  Batch ${b + 1}/${batches.length} (provisions ${start}–${end})... `);

    let parsed = null;
    let attempts = 0;

    while (attempts < 3 && !parsed) {
      attempts++;
      try {
        const response = await client.messages.create({
          model: 'claude-haiku-4-5-20251001',
          max_tokens: 1024,
          messages: [{ role: 'user', content: buildPrompt(batch) }],
        });

        const text = response.content[0].text.trim();
        // Extract JSON array even if model adds surrounding text
        const match = text.match(/\[[\s\S]*\]/);
        if (!match) throw new Error('No JSON array in response');
        parsed = JSON.parse(match[0]);

        // Validate all IDs returned
        const batchIds = new Set(batch.map(p => p.id));
        const unexpected = parsed.filter(r => !batchIds.has(r.id));
        if (unexpected.length > 0) {
          console.warn(`\n  Warning: ${unexpected.length} unexpected IDs in batch ${b + 1} response — ignoring`);
          parsed = parsed.filter(r => batchIds.has(r.id));
        }
      } catch (e) {
        if (attempts < 3) {
          process.stdout.write(`retry ${attempts}... `);
          await new Promise(r => setTimeout(r, 2000));
          parsed = null;
        } else {
          console.error(`\n  FAILED batch ${b + 1} after 3 attempts: ${e.message}`);
          errors++;
        }
      }
    }

    if (parsed) {
      results.push(...parsed);
      const counts = {};
      parsed.forEach(r => { counts[r.work_type] = (counts[r.work_type] || 0) + 1; });
      console.log(Object.entries(counts).map(([k, v]) => `${k}:${v}`).join(' '));
    }

    // Rate limit: pause briefly between batches
    if (b < batches.length - 1) await new Promise(r => setTimeout(r, 500));
  }

  console.log(`\nClassification complete. ${results.length} provisions classified, ${errors} batch errors.`);

  // Summary
  const summary = {};
  results.forEach(r => { summary[r.work_type] = (summary[r.work_type] || 0) + 1; });
  console.log('\nWork type distribution:');
  Object.entries(summary).sort((a, b) => b[1] - a[1]).forEach(([k, v]) => {
    console.log(`  ${k.padEnd(15)} ${v}`);
  });

  // Save results log regardless of dry run
  const logPath = path.join(__dirname, 'exempt-complying-classification-log.json');
  fs.writeFileSync(logPath, JSON.stringify(results, null, 2));
  console.log(`\nResults saved to: ${logPath}`);

  if (DRY_RUN) {
    console.log('\nDRY RUN — no database changes made.');
    console.log('Sample (first 20):');
    results.slice(0, 20).forEach(r => {
      const prov = rows.find(p => p.id === r.id);
      console.log(`  id=${r.id} [${r.work_type}] p${prov?.pdf_page}: ${(prov?.provision_text || '').substring(0, 80)}`);
    });
  } else {
    console.log('\nApplying to database...');

    // Map work_type labels to v2_topic values
    // 'other' and 'general' stay as-is; specific work types get capitalised labels
    const TOPIC_MAP = {
      fence: 'Fence',
      deck: 'Deck',
      carport: 'Carport',
      pool: 'Pool',
      solar_energy: 'Solar Energy',
      general: 'General',
      other: null, // leave v2_topic as null for 'other' — don't pollute with noise
    };

    let updated = 0;
    let skipped = 0;

    for (const result of results) {
      const topic = TOPIC_MAP[result.work_type];
      if (topic === null) { skipped++; continue; }

      await pool.query(
        `UPDATE regulatory_provisions SET v2_topic = $1 WHERE id = $2`,
        [topic, result.id]
      );
      updated++;
    }

    console.log(`Updated: ${updated} provisions`);
    console.log(`Skipped (other): ${skipped} provisions (v2_topic left null)`);
    console.log('\nDone. Run a spot-check before marking complete:');
    console.log(`  SELECT v2_topic, COUNT(*) FROM regulatory_provisions WHERE document_id = '${DOC_ID}' GROUP BY v2_topic ORDER BY count DESC;`);
  }

  await pool.end();
}

main().catch(e => {
  console.error('Fatal error:', e);
  process.exit(1);
});
