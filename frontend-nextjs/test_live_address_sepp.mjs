#!/usr/bin/env node
/**
 * Test live address input pipeline for SEPP provisions
 * Trace: Address → Planning Portal → SEPP provisions → PDF image links
 */

const TEST_ADDRESS = '185 Parramatta Road, Leichhardt NSW 2040';

console.log('🧪 TESTING LIVE ADDRESS SEPP PROVISION PIPELINE');
console.log('=' .repeat(70));
console.log(`Address: ${TEST_ADDRESS}`);
console.log();

// Step 1: Test Planning Portal API
console.log('STEP 1: Planning Portal API');
console.log('-'.repeat(70));

async function testPlanningPortal() {
  const encodedAddress = encodeURIComponent(TEST_ADDRESS);
  const url = `https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/address?a=${encodedAddress}&noOfRecords=1`;

  console.log(`Calling: ${url.substring(0, 100)}...`);

  try {
    const response = await fetch(url);
    const data = await response.json();

    if (data && data.length > 0) {
      const property = data[0];
      console.log(`✅ Property found: ${property.address}`);
      console.log(`   PropID: ${property.propId}`);
      console.log(`   GURASID: ${property.GURASID}`);
      console.log();

      // Step 2: Get Planning Layers
      console.log('STEP 2: Planning Layers (Special Provisions)');
      console.log('-'.repeat(70));

      const layersUrl = `https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/layerintersect?type=property&id=${property.propId}&layers=epi`;
      const layersResponse = await fetch(layersUrl);
      const layers = await layersResponse.json();

      console.log(`Total layers returned: ${layers.length}`);

      // Find Special Provisions layer
      const specialProvisions = layers.find(l => l.layerName === 'Special Provisions');

      if (specialProvisions && specialProvisions.results) {
        console.log(`\n✅ Special Provisions layer found`);
        console.log(`   Results: ${specialProvisions.results.length}`);
        console.log();

        specialProvisions.results.forEach((result, i) => {
          console.log(`   ${i+1}. ${result['EPI Name'] || 'Unknown'}`);
          console.log(`      Type: ${result['EPI Type']}`);
          console.log(`      Label: ${result.Label || result.Class || 'N/A'}`);
        });

        return { property, layers, specialProvisions };
      } else {
        console.log('❌ No Special Provisions found');
        return { property, layers };
      }
    } else {
      console.log('❌ Property not found');
      return null;
    }
  } catch (error) {
    console.error('❌ Error:', error.message);
    return null;
  }
}

// Step 3: Test local API for SEPP provisions
async function testLocalSeppApi(propertyData) {
  console.log();
  console.log('STEP 3: Local API - SEPP Provisions');
  console.log('-'.repeat(70));

  // Test structured SEPP requirements API
  const seppIds = ['housing_2021', 'sustainable_buildings_2022', 'exempt_complying_2008'];

  for (const seppId of seppIds) {
    try {
      const response = await fetch('http://localhost:3003/api/sepp/structured-requirements', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          seppId,
          developmentType: 'dwelling_house_alteration'
        })
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success && data.data?.requirements) {
          console.log(`\n✅ ${seppId}: ${data.data.requirements.length} requirements`);

          // Check PDF image URLs
          const sample = data.data.requirements[0];
          if (sample) {
            console.log(`   Sample requirement:`);
            console.log(`   - ID: ${sample.id}`);
            console.log(`   - pdf_page: ${sample.pdf_page || 'NULL'}`);
            console.log(`   - pdf_page_image_url: ${sample.pdf_page_image_url ? 'YES' : 'NULL'}`);
            console.log(`   - Text: ${sample.provision_text?.substring(0, 80)}...`);
          }
        }
      }
    } catch (error) {
      console.log(`❌ ${seppId}: ${error.message}`);
    }
  }
}

// Step 4: Check regulatory_provisions for SEPP Housing
async function testRegulatoryProvisions() {
  console.log();
  console.log('STEP 4: Database - SEPP Housing Provisions');
  console.log('-'.repeat(70));

  try {
    const response = await fetch('http://localhost:3003/api/provisions?document_id=SEPP_Housing_2021&limit=5');

    if (response.ok) {
      const data = await response.json();
      console.log(`\n✅ Query successful`);
      console.log(`   Total provisions: ${data.provisions?.length || 0}`);

      if (data.provisions && data.provisions.length > 0) {
        console.log(`\n   Sample provisions:`);
        data.provisions.slice(0, 3).forEach((p, i) => {
          console.log(`\n   ${i+1}. ID ${p.id}`);
          console.log(`      document_id: ${p.document_id}`);
          console.log(`      pdf_page: ${p.pdf_page || 'NULL'}`);
          console.log(`      pdf_page_image_url: ${p.pdf_page_image_url ? p.pdf_page_image_url.substring(0, 80) + '...' : 'NULL'}`);
          console.log(`      Text: ${p.provision_text?.substring(0, 80)}...`);
        });
      }
    }
  } catch (error) {
    console.log(`❌ Error: ${error.message}`);
  }
}

// Step 5: Check how UI constructs PDF links
console.log();
console.log('STEP 5: UI Component Analysis');
console.log('-'.repeat(70));
console.log('Checking frontend components for PDF URL construction...');
console.log();

// Run all tests
(async () => {
  const portalData = await testPlanningPortal();

  if (portalData) {
    await testLocalSeppApi(portalData);
  }

  await testRegulatoryProvisions();

  console.log();
  console.log('=' .repeat(70));
  console.log('NEXT: Check UI components for PDF link fallback logic');
  console.log('Files to check:');
  console.log('  - components/compliance/StateLevelControls.tsx');
  console.log('  - components/compliance/FormattedProvisionText.tsx');
  console.log('  - components/ui/pdf-image-modal.tsx');
})();
