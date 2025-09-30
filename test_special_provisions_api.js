/**
 * Test Special Provisions data extraction from NSW Planning API
 *
 * Tests:
 * 1. Property API returns Special Provisions layer
 * 2. SEPP data is correctly extracted (Water Use, BASIX, Thermal Energy)
 * 3. Data flows to ComplianceDashboard correctly
 */

const TEST_ADDRESS = "30 Illawarra Road, Marrickville NSW 2204";
const TEST_PROP_ID = 1972074; // From user's example

async function testPropertyAPI() {
  console.log("=== TEST 1: /api/property endpoint ===\n");

  try {
    const response = await fetch(`http://localhost:3007/api/property?address=${encodeURIComponent(TEST_ADDRESS)}`);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    console.log("✅ Property API Response Status:", response.status);
    console.log("\n📊 Property Data:");
    console.log("  - Address:", data.data.address);
    console.log("  - Zone:", data.data.constraints?.zone);
    console.log("  - LGA:", data.data.constraints?.lga);

    // Check for Planning Layers
    console.log("\n📋 Planning Layers:", data.data.planningLayers?.length || 0);

    // Find Special Provisions layer
    const specialProvisionsLayer = data.data.planningLayers?.find(
      layer => layer.layerName === "Special Provisions"
    );

    if (!specialProvisionsLayer) {
      console.log("❌ No Special Provisions layer found");
      return false;
    }

    console.log("\n🎯 Special Provisions Layer Found:");
    console.log("  - Results count:", specialProvisionsLayer.results.length);

    specialProvisionsLayer.results.forEach((result, idx) => {
      console.log(`\n  Result ${idx + 1}:`);
      console.log("    - Title:", result.title);
      console.log("    - EPI Name:", result['EPI Name']);
      console.log("    - Type:", result.Type);
      console.log("    - Class:", result.Class);
      console.log("    - Map Type:", result['Map Type']);
    });

    // Check extracted BASIX values
    console.log("\n🔍 Extracted BASIX Values:");
    console.log("  - Climate:", data.data.constraints?.basixClimate);
    console.log("  - Water:", data.data.constraints?.basixWater);
    console.log("  - Environmental:", JSON.stringify(data.data.environmental, null, 2));

    // Check applicable SEPPs
    console.log("\n📜 Applicable SEPPs:");
    console.log("  - Count:", data.data.constraints?.applicableSepps?.length || 0);
    console.log("  - List:", data.data.constraints?.applicableSepps || []);

    return true;

  } catch (error) {
    console.error("❌ Test Failed:", error.message);
    return false;
  }
}

async function testComplianceConstraintsAPI(propertyData) {
  console.log("\n\n=== TEST 2: /api/compliance/constraints endpoint ===\n");

  try {
    const response = await fetch('http://localhost:3007/api/compliance/constraints', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        address: TEST_ADDRESS,
        zone: propertyData.constraints?.zone || 'R2',
        developmentType: 'dwelling_house',
        propId: propertyData.propId
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    console.log("✅ Compliance Constraints Response Status:", response.status);
    console.log("\n📊 Constraints Summary:");
    console.log("  - Building Envelope:", data.data.building_envelope?.length || 0);
    console.log("  - Environmental:", data.data.environmental?.length || 0);
    console.log("  - Special Provisions:", data.data.special_provisions?.length || 0);
    console.log("  - SEPP Overrides:", data.data.sepp_overrides?.length || 0);

    // Check for SEPP provisions
    const seppProvisions = data.data.special_provisions?.filter(
      p => p.source.authority_level === 'SEPP'
    );

    console.log("\n🟥 SEPP Provisions Found:", seppProvisions?.length || 0);

    if (seppProvisions && seppProvisions.length > 0) {
      seppProvisions.forEach((sepp, idx) => {
        console.log(`\n  SEPP ${idx + 1}:`);
        console.log("    - Type:", sepp.type);
        console.log("    - Value:", sepp.value);
        console.log("    - Clause:", sepp.source.clause);
        console.log("    - Document:", sepp.source.document);
        console.log("    - Text preview:", sepp.full_text?.substring(0, 100) + "...");
      });
    }

    // Check processing time
    console.log("\n⏱️  Processing Time:", data.metadata?.processingTimeMs + "ms");

    return data;

  } catch (error) {
    console.error("❌ Test Failed:", error.message);
    return null;
  }
}

async function testDirectPlanningAPI() {
  console.log("\n\n=== TEST 3: Direct NSW Planning Portal API ===\n");

  try {
    const url = `https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/layerintersect?type=property&id=${TEST_PROP_ID}&layers=epi`;

    console.log("Fetching:", url);

    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const layers = await response.json();

    console.log("✅ Direct API Response Status:", response.status);
    console.log("  - Total layers:", layers.length);

    // Find Special Provisions
    const specialProvisions = layers.find(l => l.layerName === "Special Provisions");

    if (specialProvisions) {
      console.log("\n🎯 Special Provisions from NSW API:");
      console.log("  - Results:", specialProvisions.results.length);

      specialProvisions.results.forEach((result, idx) => {
        console.log(`\n  ${idx + 1}. ${result.title}`);
        console.log("     EPI:", result['EPI Name']);
        console.log("     Type:", result.Type);
        console.log("     Class:", result.Class);
      });
    } else {
      console.log("❌ No Special Provisions found in direct API call");
    }

    return layers;

  } catch (error) {
    console.error("❌ Test Failed:", error.message);
    return null;
  }
}

// Run all tests
async function runTests() {
  console.log("🚀 Starting Special Provisions API Tests\n");
  console.log("=" .repeat(60));

  // Test 1: Property API
  const test1Success = await testPropertyAPI();

  if (test1Success) {
    // Get property data for test 2
    const propertyResponse = await fetch(`http://localhost:3007/api/property?address=${encodeURIComponent(TEST_ADDRESS)}`);
    const propertyData = await propertyResponse.json();

    // Test 2: Compliance Constraints API
    await testComplianceConstraintsAPI(propertyData.data);
  }

  // Test 3: Direct API call
  await testDirectPlanningAPI();

  console.log("\n" + "=".repeat(60));
  console.log("✅ All tests completed\n");
}

runTests().catch(console.error);