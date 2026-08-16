#!/usr/bin/env node

/**
 * Test REAL Leichhardt property flow:
 * 1. Pick a Leichhardt address
 * 2. Query Planning Portal for property details
 * 3. Query local API with those filters
 * 4. Compare to database counts
 */

const API_BASE = 'http://localhost:3003';

// Test Leichhardt addresses (different zones)
const TEST_ADDRESSES = [
  '1 Balmain Road, Leichhardt NSW 2040',     // Should be B zone (commercial strip)
  '15 Marion Street, Leichhardt NSW 2040',   // Should be R2 or R3 (residential)
  '50 Norton Street, Leichhardt NSW 2040',   // Should be B1 (Norton St shopping)
];

async function queryPlanningPortal(address) {
  console.log(`\n${'='.repeat(80)}`);
  console.log(`QUERYING PLANNING PORTAL: ${address}`);
  console.log('='.repeat(80));

  try {
    const response = await fetch(`${API_BASE}/api/property?address=${encodeURIComponent(address)}`);
    const data = await response.json();

    if (!data.success || !data.data) {
      console.log('❌ Planning Portal query failed:', data.error || 'No data returned');
      return null;
    }

    const property = data.data;
    console.log('\n📍 Property Details:');
    console.log(`   Address: ${property.formatted_address}`);
    console.log(`   LGA: ${property.lga}`);
    console.log(`   Zone: ${property.zone}`);
    console.log(`   Former Council: ${property.former_council || 'N/A'}`);
    console.log(`   Heritage: ${property.is_heritage}`);
    console.log(`   Heritage Items: ${property.heritage_items?.length || 0}`);
    console.log(`   HCA: ${property.hca_name || 'None'}`);
    console.log(`   Flood: ${property.is_flood_prone || false}`);
    console.log(`   Precinct ID: ${property.precinct_id || 'None'}`);

    return property;
  } catch (error) {
    console.log('❌ Error querying Planning Portal:', error.message);
    return null;
  }
}

async function queryProvisionsAPI(property) {
  console.log(`\n${'='.repeat(80)}`);
  console.log('QUERYING PROVISIONS API');
  console.log('='.repeat(80));

  // Build API URL with property filters
  const params = new URLSearchParams({
    lga: property.lga,
    zone: property.zone,
    heritage: property.is_heritage.toString(),
    former_council: property.former_council || '',
  });

  if (property.is_flood_prone) params.append('flood', 'true');
  if (property.precinct_id) params.append('precinct_id', property.precinct_id);
  if (property.hca_code) params.append('hca', property.hca_code);

  const url = `${API_BASE}/api/provisions/for-property?${params.toString()}`;
  console.log(`\n🔗 API URL:\n   ${url}\n`);

  try {
    const response = await fetch(url);
    const data = await response.json();

    if (!data.success) {
      console.log('❌ API query failed:', data.error);
      return null;
    }

    console.log('📊 API Response Summary:');
    const summary = data.data.summary;
    console.log(`   Total provisions: ${summary.total_provisions}`);
    console.log(`   Layer 1 (generic): ${summary.layer_1_generic}`);
    console.log(`   Layer 2 (use_specific): ${summary.layer_2_use_specific}`);
    console.log(`   Layer 3 (condition): ${summary.layer_3_condition}`);
    console.log(`   Layer 4 (precinct): ${summary.layer_4_precinct}`);

    // Show topic breakdown
    console.log('\n📋 By Topic:');
    const topics = Object.entries(data.data.by_topic);
    topics.sort((a, b) => b[1].length - a[1].length);
    topics.slice(0, 10).forEach(([topic, provisions]) => {
      console.log(`   ${topic.padEnd(30)} ${provisions.length} provisions`);
    });

    // Show filters applied
    console.log('\n🔍 Filters Applied:');
    const filters = data.meta.filters_applied;
    Object.entries(filters).forEach(([key, value]) => {
      if (value) console.log(`   ${key}: ${value}`);
    });

    return data;
  } catch (error) {
    console.log('❌ Error querying API:', error.message);
    return null;
  }
}

async function compareToDatabaseExpectation(property, apiResult) {
  console.log(`\n${'='.repeat(80)}`);
  console.log('ANALYSIS');
  console.log('='.repeat(80));

  const total = apiResult.data.summary.total_provisions;

  // Expected counts for Leichhardt
  const expectedGeneric = 2309;
  const actualGeneric = apiResult.data.summary.layer_1_generic;

  console.log('\n💡 Expected vs Actual:');
  console.log(`   Generic layer (always included): Expected ~${expectedGeneric}, Got ${actualGeneric}`);

  if (actualGeneric < expectedGeneric * 0.5) {
    console.log('\n⚠️  MAJOR DISCREPANCY DETECTED:');
    console.log(`   Generic layer is missing ${expectedGeneric - actualGeneric} provisions`);
    console.log(`   This is ${((expectedGeneric - actualGeneric) / expectedGeneric * 100).toFixed(1)}% of expected provisions`);
  } else if (actualGeneric < expectedGeneric * 0.9) {
    console.log('\n⚠️  MODERATE DISCREPANCY:');
    console.log(`   Generic layer is missing ${expectedGeneric - actualGeneric} provisions`);
    console.log(`   This is ${((expectedGeneric - actualGeneric) / expectedGeneric * 100).toFixed(1)}% of expected provisions`);
  } else {
    console.log('   ✅ Generic layer count is within expected range');
  }

  console.log(`\n📈 Total provisions returned: ${total}`);

  if (total < 1000) {
    console.log('\n🔴 ISSUE CONFIRMED:');
    console.log(`   Only ${total} provisions returned for Leichhardt property`);
    console.log('   Expected: 2,300-2,900 provisions depending on filters');
    console.log('\n   Possible causes:');
    console.log('   1. API is applying filters that exclude most provisions');
    console.log('   2. Database is missing provisions after rebuild');
    console.log('   3. Deduplication is too aggressive');
    console.log('   4. Layer queries have incorrect WHERE clauses');
  } else if (total < 2000) {
    console.log('\n🟡 POTENTIAL ISSUE:');
    console.log(`   ${total} provisions returned`);
    console.log('   This is lower than expected for a typical property');
  } else {
    console.log('\n✅ Provision count looks normal for this property configuration');
  }

  // Check for precinct impact
  if (!property.precinct_id) {
    const precinctNullCount = apiResult.data.summary.layer_4_precinct;
    console.log(`\n📍 Precinct Impact:`);
    console.log(`   No precinct_id provided`);
    console.log(`   Precinct layer returned: ${precinctNullCount} provisions (NULL precinct_id only)`);
    console.log(`   Database has: 660 total precinct provisions for Leichhardt`);
    console.log(`   Excluded: ${660 - precinctNullCount} precinct-specific provisions`);
  }
}

async function runTest(address) {
  console.log('\n\n');
  console.log('█'.repeat(80));
  console.log(`TEST: ${address}`);
  console.log('█'.repeat(80));

  // Step 1: Get property details
  const property = await queryPlanningPortal(address);
  if (!property) return;

  // Step 2: Query provisions API
  const apiResult = await queryProvisionsAPI(property);
  if (!apiResult) return;

  // Step 3: Analyze results
  await compareToDatabaseExpectation(property, apiResult);
}

async function main() {
  console.log('\n🚀 LEICHHARDT REAL FLOW TEST');
  console.log('Testing actual app workflow with real addresses...\n');

  // Test first address (can add more)
  await runTest(TEST_ADDRESSES[1]); // Marion Street (residential)

  console.log('\n\n' + '='.repeat(80));
  console.log('TEST COMPLETE');
  console.log('='.repeat(80) + '\n');
}

main().catch(console.error);
