'use strict';

/**
 * fix-exempt-complying-stale-tags.cjs
 *
 * Clears stale pre-existing DCP-style v2_topic values from SEPP E&C provisions
 * that were classified as 'other' by the LLM tagger (so v2_topic was not updated,
 * leaving old values like 'signage', 'height', 'heritage', etc.).
 *
 * Valid work-type tags for this document: General, Fence, Deck, Carport, Pool, Solar Energy
 * Everything else must be nulled out.
 *
 * Usage: node fix-exempt-complying-stale-tags.cjs
 */

const { Pool } = require('./frontend-nextjs/node_modules/pg');
const path = require('path');

require('./frontend-nextjs/node_modules/dotenv').config({
  path: path.join(__dirname, 'frontend-nextjs/.env.local'),
});

const DOC_ID = 'State_Environmental_Planning_Policy_Exempt_and_Complying_Development_Codes_2008__NSW_Legislation';

const VALID_TOPICS = ['General', 'Fence', 'Deck', 'Carport', 'Pool', 'Solar Energy'];

async function main() {
  const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false },
  });

  // Count first
  const { rows: before } = await pool.query(`
    SELECT v2_topic, COUNT(*) as cnt
    FROM regulatory_provisions
    WHERE document_id = $1
      AND v2_topic IS NOT NULL
      AND v2_topic NOT IN (${VALID_TOPICS.map((_, i) => `$${i + 2}`).join(', ')})
    GROUP BY v2_topic
    ORDER BY cnt DESC
  `, [DOC_ID, ...VALID_TOPICS]);

  if (before.length === 0) {
    console.log('No stale tags found — nothing to do.');
    await pool.end();
    return;
  }

  console.log('Stale tags to clear:');
  before.forEach(r => console.log(`  ${r.v2_topic}: ${r.cnt}`));
  const total = before.reduce((sum, r) => sum + parseInt(r.cnt), 0);
  console.log(`Total: ${total} provisions`);

  const { rowCount } = await pool.query(`
    UPDATE regulatory_provisions
    SET v2_topic = NULL
    WHERE document_id = $1
      AND v2_topic IS NOT NULL
      AND v2_topic NOT IN (${VALID_TOPICS.map((_, i) => `$${i + 2}`).join(', ')})
  `, [DOC_ID, ...VALID_TOPICS]);

  console.log(`\nCleared: ${rowCount} provisions set to v2_topic = NULL`);

  await pool.end();
}

main().catch(e => { console.error('Fatal:', e); process.exit(1); });
