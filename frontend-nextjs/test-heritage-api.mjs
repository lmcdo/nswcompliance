/**
 * Test heritage provisions API with live calls
 * Tests 33 Cardigan Street (Marrickville HCA 10)
 */

const BASE_URL = 'http://localhost:3003';

async function testHeritageProvisions() {
  console.log('=== TESTING HERITAGE PROVISIONS API ===\n');

  // Test 1: 33 Cardigan Street (Marrickville HCA 10, precinct 29_)
  const test1Params = new URLSearchParams({
    lga: 'Inner West',
    zone: 'R1',
    heritage: 'true',
    former_council: 'Marrickville',
    hca: 'hca_10',
    precinct_id: '29_',
    topic: 'roof'  // Filter to Roof provisions only
  });

  console.log('Test 1: 33 Cardigan St - Roof provisions (no type filter)');
  console.log('URL:', `${BASE_URL}/api/provisions/for-property?${test1Params}`);

  try {
    const response = await fetch(`${BASE_URL}/api/provisions/for-property?${test1Params}`);
    const data = await response.json();

    if (data.success) {
      console.log('\n✅ SUCCESS');
      console.log('Total provisions:', data.data.summary.total_provisions);

      // Check layer breakdown
      const layer3 = data.data.by_layer.find(l => l.layer === 'condition');
      console.log('\nLayer 3 (Heritage Condition):', layer3?.count || 0, 'provisions');

      if (layer3 && layer3.provisions.length > 0) {
        // Group by v2_heritage_type
        const typeBreakdown = {};
        layer3.provisions.forEach(p => {
          const type = p.v2_heritage_type || 'NULL';
          typeBreakdown[type] = (typeBreakdown[type] || 0) + 1;
        });

        console.log('\nBreakdown by v2_heritage_type:');
        Object.entries(typeBreakdown).forEach(([type, count]) => {
          console.log(`  ${type}: ${count}`);
        });

        // Show sample provisions
        console.log('\nSample provisions (first 3):');
        layer3.provisions.slice(0, 3).forEach((p, i) => {
          console.log(`\n${i + 1}. Type: ${p.v2_heritage_type || 'NULL'}`);
          console.log(`   Topic: ${p.v2_topic}`);
          console.log(`   Text: ${p.provision_text.substring(0, 100)}...`);
        });
      }
    } else {
      console.log('❌ FAILED:', data.error);
    }
  } catch (error) {
    console.log('❌ ERROR:', error.message);
  }

  // Test 2: Same property but with heritage_type=control filter
  console.log('\n\n' + '='.repeat(60));
  console.log('\nTest 2: 33 Cardigan St - Roof CONTROLS only (heritage_type=control)');

  const test2Params = new URLSearchParams({
    lga: 'Inner West',
    zone: 'R1',
    heritage: 'true',
    former_council: 'Marrickville',
    hca: 'hca_10',
    precinct_id: '29_',
    topic: 'roof',
    heritage_type: 'control'  // NEW FILTER
  });

  console.log('URL:', `${BASE_URL}/api/provisions/for-property?${test2Params}`);

  try {
    const response = await fetch(`${BASE_URL}/api/provisions/for-property?${test2Params}`);
    const data = await response.json();

    if (data.success) {
      console.log('\n✅ SUCCESS');
      const layer3 = data.data.by_layer.find(l => l.layer === 'condition');
      console.log('Layer 3 (Heritage Controls):', layer3?.count || 0, 'provisions');

      if (layer3 && layer3.provisions.length > 0) {
        console.log('\nSample controls (first 5):');
        layer3.provisions.slice(0, 5).forEach((p, i) => {
          console.log(`\n${i + 1}. Type: ${p.v2_heritage_type}`);
          console.log(`   Text: ${p.provision_text.substring(0, 120)}...`);
        });
      }
    } else {
      console.log('❌ FAILED:', data.error);
    }
  } catch (error) {
    console.log('❌ ERROR:', error.message);
  }

  // Test 3: Character statements only
  console.log('\n\n' + '='.repeat(60));
  console.log('\nTest 3: 33 Cardigan St - Roof CHARACTER statements (heritage_type=character)');

  const test3Params = new URLSearchParams({
    lga: 'Inner West',
    zone: 'R1',
    heritage: 'true',
    former_council: 'Marrickville',
    hca: 'hca_10',
    precinct_id: '29_',
    topic: 'roof',
    heritage_type: 'character'
  });

  try {
    const response = await fetch(`${BASE_URL}/api/provisions/for-property?${test3Params}`);
    const data = await response.json();

    if (data.success) {
      console.log('\n✅ SUCCESS');
      const layer3 = data.data.by_layer.find(l => l.layer === 'condition');
      console.log('Layer 3 (Heritage Character):', layer3?.count || 0, 'provisions');

      if (layer3 && layer3.provisions.length > 0) {
        console.log('\nCharacter statements:');
        layer3.provisions.forEach((p, i) => {
          console.log(`\n${i + 1}. ${p.provision_text.substring(0, 150)}...`);
        });
      }
    } else {
      console.log('❌ FAILED:', data.error);
    }
  } catch (error) {
    console.log('❌ ERROR:', error.message);
  }
}

testHeritageProvisions().catch(console.error);
