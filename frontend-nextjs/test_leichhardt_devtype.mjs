#!/usr/bin/env node

/**
 * Test Leichhardt provision counts and dev_type effectiveness
 *
 * Questions to answer:
 * 1. How many provisions for Leichhardt property without filters?
 * 2. Does dev_type filtering reduce count significantly?
 * 3. How many provisions have v2_applicable_dev_types tagged?
 */

const TEST_CASES = [
  {
    name: "Leichhardt Dwelling House - No Dev Type",
    params: {
      lga: "Inner West",
      zone: "R2",
      heritage: false,
      former_council: "leichhardt",
      // NO dev_type parameter
    }
  },
  {
    name: "Leichhardt Dwelling House - With Dev Type",
    params: {
      lga: "Inner West",
      zone: "R2",
      heritage: false,
      former_council: "leichhardt",
      dev_type: "dwelling_house"
    }
  },
  {
    name: "Leichhardt Commercial - No Dev Type",
    params: {
      lga: "Inner West",
      zone: "B1",
      heritage: false,
      former_council: "leichhardt",
    }
  },
  {
    name: "Leichhardt Commercial - With Dev Type",
    params: {
      lga: "Inner West",
      zone: "B1",
      heritage: false,
      former_council: "leichhardt",
      dev_type: "shop"
    }
  }
];

async function testCase(testCase) {
  const url = new URL('http://localhost:3003/api/provisions/for-property');
  Object.entries(testCase.params).forEach(([key, value]) => {
    url.searchParams.append(key, value);
  });

  console.log(`\n${'='.repeat(80)}`);
  console.log(`TEST: ${testCase.name}`);
  console.log(`URL: ${url.toString()}`);
  console.log(`${'='.repeat(80)}`);

  try {
    const response = await fetch(url);
    const data = await response.json();

    if (!data.success) {
      console.error('❌ API Error:', data.error);
      return;
    }

    // Count total provisions across all layers
    const totalCount = data.data.by_layer.reduce((sum, layer) => sum + layer.count, 0);

    console.log(`\n📊 PROVISION COUNTS:`);
    console.log(`   Total: ${totalCount}`);
    data.data.by_layer.forEach(layer => {
      console.log(`   - ${layer.layer_name}: ${layer.count}`);
    });

    // Analyze dev_type tagging
    const allProvisions = data.data.by_layer.flatMap(layer => layer.provisions);

    const devTypeTagged = allProvisions.filter(p =>
      p.v2_applicable_dev_types &&
      p.v2_applicable_dev_types.length > 0 &&
      !p.v2_applicable_dev_types.includes('ALL')
    );

    const allDevTypes = allProvisions.filter(p =>
      p.v2_applicable_dev_types &&
      p.v2_applicable_dev_types.includes('ALL')
    );

    const untagged = allProvisions.filter(p => !p.v2_applicable_dev_types);

    console.log(`\n🏷️  DEV_TYPE TAGGING:`);
    console.log(`   Explicitly tagged: ${devTypeTagged.length} (${((devTypeTagged.length/totalCount)*100).toFixed(1)}%)`);
    console.log(`   Tagged as 'ALL': ${allDevTypes.length} (${((allDevTypes.length/totalCount)*100).toFixed(1)}%)`);
    console.log(`   Untagged (NULL): ${untagged.length} (${((untagged.length/totalCount)*100).toFixed(1)}%)`);

    // Show relevance breakdown if dev_type was provided
    if (testCase.params.dev_type && data.data.summary.relevance_breakdown) {
      console.log(`\n🎯 RELEVANCE BREAKDOWN:`);
      console.log(`   Primary: ${data.data.summary.relevance_breakdown.primary || 0}`);
      console.log(`   General: ${data.data.summary.relevance_breakdown.general || 0}`);
      console.log(`   Secondary: ${data.data.summary.relevance_breakdown.secondary || 0}`);
    }

    // Sample provisions to understand structure
    console.log(`\n📝 SAMPLE PROVISIONS (first 3):`);
    allProvisions.slice(0, 3).forEach((p, i) => {
      console.log(`\n   ${i+1}. ${p.provision_text?.substring(0, 100)}...`);
      console.log(`      Layer: ${p.v2_dcp_layer}, Topic: ${p.v2_topic || 'N/A'}`);
      console.log(`      Dev Types: ${p.v2_applicable_dev_types?.join(', ') || 'NULL'}`);
      console.log(`      Marker: ${p.v2_marker || 'N/A'}`);
    });

  } catch (error) {
    console.error('❌ Test failed:', error.message);
  }
}

async function runAllTests() {
  console.log('🚀 Starting Leichhardt Dev Type Analysis...\n');

  for (const test of TEST_CASES) {
    await testCase(test);
    await new Promise(resolve => setTimeout(resolve, 500)); // Brief pause between tests
  }

  console.log(`\n${'='.repeat(80)}`);
  console.log('✅ All tests complete');
  console.log(`${'='.repeat(80)}\n`);
}

runAllTests().catch(console.error);
