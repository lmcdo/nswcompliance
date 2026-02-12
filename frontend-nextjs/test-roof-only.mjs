/**
 * Test Roof-specific heritage provision filtering
 */

const BASE_URL = 'http://localhost:3003';

async function testRoofFiltering() {
  console.log('=== TESTING ROOF-SPECIFIC HERITAGE FILTERING ===\n');

  // Test with lowercase "roof"
  const test1Params = new URLSearchParams({
    lga: 'Inner West',
    zone: 'R1',
    heritage: 'true',
    former_council: 'Marrickville',
    hca: 'hca_10',
    precinct_id: '29_',
    topic: 'roof'  // lowercase
  });

  console.log('Test 1: topic=roof (lowercase)');
  const r1 = await fetch(`${BASE_URL}/api/provisions/for-property?${test1Params}`);
  const d1 = await r1.json();
  const layer1 = d1.data?.by_layer?.find(l => l.layer === 'condition');
  console.log(`Result: ${layer1?.count || 0} provisions`);

  // Test with capitalized "Roof"
  const test2Params = new URLSearchParams({
    lga: 'Inner West',
    zone: 'R1',
    heritage: 'true',
    former_council: 'Marrickville',
    hca: 'hca_10',
    precinct_id: '29_',
    topic: 'Roof'  // Capitalized
  });

  console.log('\nTest 2: topic=Roof (capitalized)');
  const r2 = await fetch(`${BASE_URL}/api/provisions/for-property?${test2Params}`);
  const d2 = await r2.json();
  const layer2 = d2.data?.by_layer?.find(l => l.layer === 'condition');
  console.log(`Result: ${layer2?.count || 0} provisions`);

  if (layer2 && layer2.count > 0) {
    // Show v2_heritage_type breakdown for Roof
    const typeBreakdown = {};
    layer2.provisions.forEach(p => {
      const type = p.v2_heritage_type || 'NULL';
      typeBreakdown[type] = (typeBreakdown[type] || 0) + 1;
    });

    console.log('\nBreakdown by heritage_type:');
    Object.entries(typeBreakdown).forEach(([type, count]) => {
      console.log(`  ${type}: ${count}`);
    });
  }

  // Test 3: Roof + Controls only
  console.log('\n' + '='.repeat(60));
  console.log('\nTest 3: Roof CONTROLS only (topic=Roof&heritage_type=control)');

  const test3Params = new URLSearchParams({
    lga: 'Inner West',
    zone: 'R1',
    heritage: 'true',
    former_council: 'Marrickville',
    hca: 'hca_10',
    precinct_id: '29_',
    topic: 'Roof',
    heritage_type: 'control'
  });

  const r3 = await fetch(`${BASE_URL}/api/provisions/for-property?${test3Params}`);
  const d3 = await r3.json();
  const layer3 = d3.data?.by_layer?.find(l => l.layer === 'condition');
  console.log(`Result: ${layer3?.count || 0} roof control provisions`);

  if (layer3 && layer3.count > 0) {
    console.log('\nSample Roof Controls:');
    layer3.provisions.slice(0, 5).forEach((p, i) => {
      console.log(`\n${i + 1}. ${p.provision_text.substring(0, 150)}...`);
    });
  }

  // Test 4: Roof + Character only
  console.log('\n' + '='.repeat(60));
  console.log('\nTest 4: Roof CHARACTER statements (topic=Roof&heritage_type=character)');

  const test4Params = new URLSearchParams({
    lga: 'Inner West',
    zone: 'R1',
    heritage: 'true',
    former_council: 'Marrickville',
    hca: 'hca_10',
    precinct_id: '29_',
    topic: 'Roof',
    heritage_type: 'character'
  });

  const r4 = await fetch(`${BASE_URL}/api/provisions/for-property?${test4Params}`);
  const d4 = await r4.json();
  const layer4 = d4.data?.by_layer?.find(l => l.layer === 'condition');
  console.log(`Result: ${layer4?.count || 0} roof character provisions`);

  console.log('\n' + '='.repeat(60));
  console.log('\n✅ SUMMARY:');
  console.log(`Roof (all types): ${layer2?.count || 0}`);
  console.log(`Roof Controls: ${layer3?.count || 0}`);
  console.log(`Roof Character: ${layer4?.count || 0}`);
  const reduction = Math.round(((layer3?.count || 0) / (layer2?.count || 1)) * 100);
  console.log(`\nReduction: ${layer2?.count || 0} → ${layer3?.count || 0} controls (${reduction}% retention)`);
}

testRoofFiltering().catch(console.error);
