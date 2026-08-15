#!/usr/bin/env node

/**
 * Test Leichhardt provisions API directly with typical parameters
 */

const API_BASE = 'http://localhost:3003';

// Test cases: typical Leichhardt properties
const TEST_CASES = [
  {
    name: 'Leichhardt R2 (no heritage, no precinct)',
    params: {
      lga: 'Inner West',
      zone: 'R2',
      heritage: 'false',
      former_council: 'leichhardt',
    }
  },
  {
    name: 'Leichhardt R2 (with heritage, no HCA)',
    params: {
      lga: 'Inner West',
      zone: 'R2',
      heritage: 'true',
      former_council: 'leichhardt',
    }
  },
  {
    name: 'Leichhardt B1 Norton Street (commercial)',
    params: {
      lga: 'Inner West',
      zone: 'B1',
      heritage: 'false',
      former_council: 'leichhardt',
    }
  },
];

async function testCase(testCase) {
  console.log('\n' + '='.repeat(80));
  console.log(`TEST: ${testCase.name}`);
  console.log('='.repeat(80));

  const url = new URL(`${API_BASE}/api/provisions/for-property`);
  Object.entries(testCase.params).forEach(([key, value]) => {
    url.searchParams.append(key, value);
  });

  console.log(`\n🔗 API URL:\n   ${url.toString()}\n`);

  try {
    const response = await fetch(url);
    const data = await response.json();

    if (!data.success) {
      console.log('❌ API Error:', data.error);
      return;
    }

    const summary = data.data.summary;
    console.log('📊 PROVISION COUNTS:');
    console.log(`   Total:          ${summary.total_provisions}`);
    console.log(`   Layer 1 (generic):       ${summary.layer_1_generic}`);
    console.log(`   Layer 2 (use_specific):  ${summary.layer_2_use_specific}`);
    console.log(`   Layer 3 (condition):     ${summary.layer_3_condition}`);
    console.log(`   Layer 4 (precinct):      ${summary.layer_4_precinct}`);

    // Show layer breakdown
    console.log('\n📋 LAYER DETAILS:');
    data.data.by_layer.forEach(layer => {
      console.log(`   ${layer.layer_name.padEnd(30)} ${layer.count} provisions`);
    });

    // Show top topics
    console.log('\n🏷️  TOP TOPICS:');
    const topics = Object.entries(data.data.by_topic);
    topics.sort((a, b) => b[1].length - a[1].length);
    topics.slice(0, 10).forEach(([topic, provisions]) => {
      console.log(`   ${topic.padEnd(30)} ${provisions.length}`);
    });

    // Analysis
    console.log('\n💡 ANALYSIS:');

    const expectedGeneric = 2309;
    const actualGeneric = summary.layer_1_generic;
    const genericDiff = expectedGeneric - actualGeneric;
    const genericPct = (genericDiff / expectedGeneric * 100);

    if (Math.abs(genericPct) > 10) {
      console.log(`   ⚠️  Generic layer: Expected ${expectedGeneric}, got ${actualGeneric} (${genericPct > 0 ? '-' : '+'}${Math.abs(genericPct).toFixed(1)}%)`);
    } else {
      console.log(`   ✅ Generic layer: ${actualGeneric} (within 10% of expected ${expectedGeneric})`);
    }

    if (summary.total_provisions < 1000) {
      console.log(`   🔴 ISSUE: Only ${summary.total_provisions} provisions returned`);
      console.log('      Expected: 2,300-2,900 for typical Leichhardt property');
    } else if (summary.total_provisions < 2000) {
      console.log(`   🟡 LOW: ${summary.total_provisions} provisions (lower than expected)`);
    } else {
      console.log(`   ✅ Total: ${summary.total_provisions} provisions (normal range)`);
    }

    // Check deduplication impact
    const layerSum = data.data.by_layer.reduce((sum, l) => sum + l.count, 0);
    if (layerSum !== summary.total_provisions) {
      console.log(`   ℹ️  Deduplication: Layer sum ${layerSum} → Final ${summary.total_provisions} (removed ${layerSum - summary.total_provisions})`);
    }

    return summary;

  } catch (error) {
    console.log('❌ Test failed:', error.message);
    console.log('   Make sure Next.js dev server is running: npm run dev');
    return null;
  }
}

async function main() {
  console.log('\n🚀 LEICHHARDT API DIRECT TEST');
  console.log('Testing provisions API with typical Leichhardt property parameters\n');

  const results = [];

  for (const test of TEST_CASES) {
    const result = await testCase(test);
    if (result) {
      results.push({ name: test.name, ...result });
    }
    await new Promise(resolve => setTimeout(resolve, 500)); // Brief pause
  }

  // Summary
  console.log('\n\n' + '='.repeat(80));
  console.log('SUMMARY');
  console.log('='.repeat(80));

  results.forEach(r => {
    console.log(`\n${r.name}:`);
    console.log(`  Total: ${r.total_provisions}`);
    console.log(`  Generic: ${r.layer_1_generic}, Use-specific: ${r.layer_2_use_specific}, Condition: ${r.layer_3_condition}, Precinct: ${r.layer_4_precinct}`);
  });

  // Compare to database expectation
  console.log('\n\n📊 DATABASE COMPARISON:');
  console.log('  Leichhardt database has:');
  console.log('    - 2,990 total actionable provisions');
  console.log('    - 2,309 generic');
  console.log('    - 21 use_specific');
  console.log('    - 0 condition');
  console.log('    - 660 precinct');
  console.log('\n  For a property with NO precinct_id:');
  console.log('    - Expected: ~2,330 provisions (2,309 generic + 21 use_specific + 0 precinct-null)');
  console.log(`    - Actual: ${results[0]?.total_provisions || 'N/A'}`);

  if (results[0] && results[0].total_provisions < 1500) {
    console.log('\n  🔴 CONFIRMED: API is returning significantly fewer provisions than expected');
    console.log('     This matches the reported issue: "800+ instead of 2k+"');
  }

  console.log('\n' + '='.repeat(80) + '\n');
}

main().catch(console.error);
