#!/usr/bin/env node

/**
 * Marrickville DevType Investigation - API Testing
 *
 * OBJECTIVE: Use real API calls to determine:
 * 1. How many Marrickville provisions are returned by the API?
 * 2. Does dev_type filtering reduce the count?
 * 3. What is the actual dev_type tagging status?
 * 4. What is the best DevType strategy for Marrickville?
 *
 * This investigation is data-driven, not assumption-based.
 * For database queries, see marrickville_db_analysis.sql
 */

const TEST_CASES = [
  {
    name: "Marrickville Residential - No Dev Type",
    params: {
      lga: "Inner West",
      zone: "R2",
      heritage: false,
      former_council: "marrickville",
    }
  },
  {
    name: "Marrickville Residential - With Dev Type (Dwelling House)",
    params: {
      lga: "Inner West",
      zone: "R2",
      heritage: false,
      former_council: "marrickville",
      dev_type: "dwelling_house"
    }
  },
  {
    name: "Marrickville Commercial - No Dev Type",
    params: {
      lga: "Inner West",
      zone: "B2",
      heritage: false,
      former_council: "marrickville",
    }
  },
  {
    name: "Marrickville Commercial - With Dev Type (Shop)",
    params: {
      lga: "Inner West",
      zone: "B2",
      heritage: false,
      former_council: "marrickville",
      dev_type: "shop"
    }
  },
  {
    name: "Marrickville Mixed Use - With Dev Type (Multi Dwelling)",
    params: {
      lga: "Inner West",
      zone: "R3",
      heritage: false,
      former_council: "marrickville",
      dev_type: "multi_dwelling_housing"
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
  console.log(`PARAMS: former_council=${testCase.params.former_council}, zone=${testCase.params.zone}, dev_type=${testCase.params.dev_type || 'NONE'}`);
  console.log(`${'='.repeat(80)}`);

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);

    const response = await fetch(url, { signal: controller.signal });
    clearTimeout(timeout);

    const data = await response.json();

    if (!data.success) {
      console.error('❌ API Error:', data.error);
      return null;
    }

    // Count total provisions across all layers
    const totalCount = data.data.by_layer.reduce((sum, layer) => sum + layer.count, 0);

    console.log(`\n📊 PROVISION COUNTS:`);
    console.log(`   Total: ${totalCount}`);

    if (totalCount > 0) {
      data.data.by_layer.forEach(layer => {
        console.log(`   - ${layer.layer_name.padEnd(30)} ${layer.count.toString().padStart(4)}`);
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
      console.log(`   Explicitly tagged: ${devTypeTagged.length.toString().padStart(4)} (${((devTypeTagged.length/totalCount)*100).toFixed(1)}%)`);
      console.log(`   Tagged as 'ALL':   ${allDevTypes.length.toString().padStart(4)} (${((allDevTypes.length/totalCount)*100).toFixed(1)}%)`);
      console.log(`   Untagged (NULL):   ${untagged.length.toString().padStart(4)} (${((untagged.length/totalCount)*100).toFixed(1)}%)`);

      // Show relevance breakdown if dev_type was provided
      if (testCase.params.dev_type && data.data.summary.relevance_breakdown) {
        console.log(`\n🎯 RELEVANCE BREAKDOWN:`);
        console.log(`   Primary:   ${(data.data.summary.relevance_breakdown.primary || 0).toString().padStart(4)}`);
        console.log(`   General:   ${(data.data.summary.relevance_breakdown.general || 0).toString().padStart(4)}`);
        console.log(`   Secondary: ${(data.data.summary.relevance_breakdown.secondary || 0).toString().padStart(4)}`);
      }

      // Sample provisions to understand structure
      console.log(`\n📝 SAMPLE PROVISIONS (first 3):`);
      allProvisions.slice(0, 3).forEach((p, i) => {
        console.log(`\n   ${i+1}. ${p.provision_text?.substring(0, 80)}...`);
        console.log(`      Layer: ${p.v2_dcp_layer}, Topic: ${p.v2_topic || 'N/A'}`);
        console.log(`      Dev Types: ${p.v2_applicable_dev_types?.join(', ') || 'NULL'}`);
        console.log(`      Marker: ${p.v2_marker || 'N/A'}`);
      });

      return { testCase, totalCount, devTypeTagged: devTypeTagged.length, untagged: untagged.length, data };

    } else {
      console.log(`⚠️  No provisions returned`);
      return { testCase, totalCount: 0, devTypeTagged: 0, untagged: 0, data };
    }

  } catch (error) {
    if (error.name === 'AbortError') {
      console.error('❌ API timeout (15s exceeded)');
    } else {
      console.error('❌ Test failed:', error.message);
    }
    return null;
  }
}

function generateRecommendations(results) {
  console.log(`\n${'='.repeat(80)}`);
  console.log('💡 DATA-DRIVEN RECOMMENDATIONS');
  console.log(`${'='.repeat(80)}`);

  const validResults = results.filter(r => r !== null);

  if (validResults.length === 0) {
    console.log('\n❌ NO VALID RESULTS - Cannot generate recommendations');
    console.log('\nPossible causes:');
    console.log('  - Dev server not running on port 3003');
    console.log('  - Database connection issues');
    console.log('  - API errors');
    return;
  }

  const hasAnyProvisions = validResults.some(r => r.totalCount > 0);
  const hasDevTypeFiltering = validResults.some(r =>
    r.testCase.params.dev_type && r.totalCount > 0
  );
  const hasDevTypeTags = validResults.some(r => r.devTypeTagged > 0);

  console.log(`\n📋 FINDINGS:`);
  console.log(`   1. API returns Marrickville provisions: ${hasAnyProvisions ? 'YES' : 'NO'}`);
  console.log(`   2. DevType filtering works: ${hasDevTypeFiltering ? 'YES' : 'NO'}`);
  console.log(`   3. DevType tags present: ${hasDevTypeTags ? 'YES' : 'NO'}`);

  console.log(`\n✅ RECOMMENDED DEVTYPE STRATEGY FOR MARRICKVILLE:`);

  if (!hasAnyProvisions) {
    console.log(`   ⚠️  NO PROVISIONS RETURNED BY API`);
    console.log(`   → Action: Run marrickville_db_analysis.sql to check database directly`);
    console.log(`   → Possible: Data not loaded, or API query logic issue`);
  } else if (!hasDevTypeTags) {
    console.log(`   ⚠️  NO DEV_TYPE TAGS FOUND`);
    console.log(`   → Strategy: TOPIC-BASED FILTERING ONLY`);
    console.log(`   → Reason: Without dev_type tags, filtering would incorrectly exclude provisions`);
    console.log(`   → UI: DO NOT show dev_type dropdown for Marrickville`);
    console.log(`   → Legal: Topic-based filtering maintains EP&A Act 4.15 compliance`);
  } else {
    const avgTaggedPercent = validResults
      .filter(r => r.totalCount > 0)
      .reduce((sum, r) => sum + (r.devTypeTagged / r.totalCount), 0) / validResults.filter(r => r.totalCount > 0).length * 100;

    console.log(`   ✅ DEV_TYPE TAGS FOUND (avg ${avgTaggedPercent.toFixed(1)}% of provisions)`);
    console.log(`   → Strategy: HYBRID - Topic + DevType filtering`);
    console.log(`   → UI: SHOW dev_type dropdown for Marrickville`);
    console.log(`   → Legal: Filtering reduces noise while maintaining completeness`);

    if (avgTaggedPercent < 50) {
      console.log(`\n   ⚠️  WARNING: Less than 50% of provisions have dev_type tags`);
      console.log(`   → Risk: Some provisions may be missed if users always select dev_type`);
      console.log(`   → Mitigation: Include 'ALL' tagged provisions in results (already implemented)`);
    }
  }

  console.log(`\n📊 DETAILED RESULTS:`);
  validResults.forEach((result, i) => {
    console.log(`\n   Test ${i+1}: ${result.testCase.name}`);
    console.log(`     Total provisions: ${result.totalCount}`);
    console.log(`     Dev-type tagged: ${result.devTypeTagged}`);
    console.log(`     Untagged: ${result.untagged}`);
  });
}

async function runAllTests() {
  console.log('\n' + '█'.repeat(80));
  console.log('🔍 MARRICKVILLE DEVTYPE INVESTIGATION');
  console.log('    Real data, real answers, real strategy');
  console.log('█'.repeat(80));

  const results = [];

  for (const test of TEST_CASES) {
    const result = await testCase(test);
    if (result) results.push(result);
    await new Promise(resolve => setTimeout(resolve, 500));
  }

  generateRecommendations(results);

  console.log(`\n${'█'.repeat(80)}`);
  console.log('✅ Investigation complete');
  console.log('█'.repeat(80) + '\n');
}

runAllTests().catch(console.error);
