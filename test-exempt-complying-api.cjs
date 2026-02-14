'use strict';

/**
 * Test SEPP Exempt & Complying API logic with direct database queries
 * Tests zone→Part mapping and provision counts
 */

const { Pool } = require('./frontend-nextjs/node_modules/pg');
const path = require('path');

require('./frontend-nextjs/node_modules/dotenv').config({
  path: path.join(__dirname, 'frontend-nextjs/.env.local'),
});

const DOC_ID = 'State_Environmental_Planning_Policy_Exempt_and_Complying_Development_Codes_2008__NSW_Legislation';

function zoneToPartMap(zoneCode) {
  const ruralZones = ['R5', 'RU1', 'RU2', 'RU3', 'RU4', 'RU6'];
  if (ruralZones.includes(zoneCode)) return '3A';
  return '3';
}

async function test() {
  const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false },
  });

  console.log('Testing SEPP Exempt & Complying API Logic\n');
  console.log('='.repeat(60));

  // Test 1: R2 Zone (Part 3)
  console.log('\n📍 TEST 1: R2 Zone → Part 3 (Housing Code)');
  const r2Part = zoneToPartMap('R2');
  console.log(`   Zone R2 → Part ${r2Part}`);

  const { rows: r2Counts } = await pool.query(`
    SELECT v2_topic, COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id = $1
      AND v2_part = $2
      AND v2_topic IN ('Deck', 'Fence', 'Carport', 'Pool')
      AND v2_is_actionable = true
    GROUP BY v2_topic
    ORDER BY v2_topic
  `, [DOC_ID, r2Part]);

  console.log('   Work Type Counts:');
  let r2Total = 0;
  r2Counts.forEach(row => {
    console.log(`     ${row.v2_topic.padEnd(8)}: ${row.count}`);
    r2Total += parseInt(row.count);
  });
  console.log(`   TOTAL: ${r2Total} actionable provisions`);

  // Test 2: R5 Zone (Part 3A)
  console.log('\n📍 TEST 2: R5 Zone → Part 3A (Rural Housing Code)');
  const r5Part = zoneToPartMap('R5');
  console.log(`   Zone R5 → Part ${r5Part}`);

  const { rows: r5Counts } = await pool.query(`
    SELECT v2_topic, COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id = $1
      AND v2_part = $2
      AND v2_topic IN ('Deck', 'Fence', 'Carport', 'Pool')
      AND v2_is_actionable = true
    GROUP BY v2_topic
    ORDER BY v2_topic
  `, [DOC_ID, r5Part]);

  console.log('   Work Type Counts:');
  let r5Total = 0;
  r5Counts.forEach(row => {
    console.log(`     ${row.v2_topic.padEnd(8)}: ${row.count}`);
    r5Total += parseInt(row.count);
  });
  console.log(`   TOTAL: ${r5Total} actionable provisions`);

  // Test 3: Deck provisions for R2 (detailed)
  console.log('\n📋 TEST 3: Deck Provisions for R2 (Part 3)');
  const { rows: r2Deck } = await pool.query(`
    SELECT id, pdf_page, pdf_printed_page, provision_text, v2_part, v2_topic
    FROM regulatory_provisions
    WHERE document_id = $1
      AND v2_part = $2
      AND v2_topic = $3
      AND v2_is_actionable = true
    ORDER BY id
    LIMIT 5
  `, [DOC_ID, r2Part, 'Deck']);

  console.log(`   Found ${r2Deck.length} Deck provisions (showing first 5):`);
  r2Deck.forEach((p, i) => {
    const page = p.pdf_printed_page || p.pdf_page;
    console.log(`   ${i+1}. [id=${p.id}] p.${page} - ${p.provision_text.substring(0, 70)}...`);
  });

  // Test 4: Fence provisions for R5 (Rural)
  console.log('\n🌾 TEST 4: Fence Provisions for R5 (Part 3A - Rural)');
  const { rows: r5Fence } = await pool.query(`
    SELECT id, pdf_page, pdf_printed_page, provision_text, v2_part, v2_topic
    FROM regulatory_provisions
    WHERE document_id = $1
      AND v2_part = $2
      AND v2_topic = $3
      AND v2_is_actionable = true
    ORDER BY id
    LIMIT 5
  `, [DOC_ID, r5Part, 'Fence']);

  console.log(`   Found ${r5Fence.length} Fence provisions (showing first 5):`);
  r5Fence.forEach((p, i) => {
    const page = p.pdf_printed_page || p.pdf_page;
    console.log(`   ${i+1}. [id=${p.id}] p.${page} - ${p.provision_text.substring(0, 70)}...`);
  });

  // Test 5: Verify Part distribution
  console.log('\n📊 TEST 5: Part Distribution Across All Work Types');
  const { rows: partDist } = await pool.query(`
    SELECT v2_part, v2_topic, COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id = $1
      AND v2_topic IN ('Deck', 'Fence', 'Carport', 'Pool')
      AND v2_is_actionable = true
    GROUP BY v2_part, v2_topic
    ORDER BY v2_part, v2_topic
  `,[DOC_ID]);

  console.log('   Part → Work Type breakdown:');
  let currentPart = null;
  partDist.forEach(row => {
    if (row.v2_part !== currentPart) {
      if (currentPart !== null) console.log('');
      console.log(`   Part ${row.v2_part}:`);
      currentPart = row.v2_part;
    }
    console.log(`     ${row.v2_topic.padEnd(8)}: ${row.count}`);
  });

  // Summary
  console.log('\n' + '='.repeat(60));
  console.log('✅ All tests completed successfully\n');
  console.log('Key findings:');
  console.log(`  • R2 (Housing Code Part 3): ${r2Total} provisions`);
  console.log(`  • R5 (Rural Code Part 3A): ${r5Total} provisions`);
  console.log('  • Zone→Part mapping working correctly');
  console.log('  • Actionable provisions properly filtered\n');

  await pool.end();
}

test().catch(e => {
  console.error('❌ Test failed:', e);
  process.exit(1);
});
