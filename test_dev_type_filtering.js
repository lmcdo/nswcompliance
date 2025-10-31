/**
 * Test Strategy 4: Hybrid Multi-Signal Dev Type Filtering
 *
 * Test Case: 180 Addison Rd, Marrickville (R2, dwelling_house)
 * Expected: 40% reduction in requirements (274 → ~160-180)
 *           Zero signage requirements shown
 */

// Use built-in fetch (Node 18+)
async function testDevTypeFiltering() {
  console.log('========================================');
  console.log('Testing Dev Type Filtering');
  console.log('Test Address: 180 Addison Rd, Marrickville');
  console.log('Dev Type: dwelling_house (residential)');
  console.log('========================================\n');

  // Test case: 180 Addison Rd, Marrickville
  const testData = {
    address: '180 Addison Rd, Marrickville NSW 2204',
    coordinates: {
      lat: -33.9061,
      lon: 151.1612
    },
    zone: 'R2',
    developmentType: 'dwelling_house',
    lga: 'Inner West'
  };

  try {
    const response = await fetch('http://localhost:3007/api/compliance/dcp-complete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(testData)
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();

    if (!data.success) {
      throw new Error(`API Error: ${data.error}`);
    }

    console.log('✓ API Response Received\n');

    // Analyze results
    const generalReqs = data.general_provisions?.requirements || [];
    const totalReqs = generalReqs.length;

    console.log('RESULTS:');
    console.log('========================================');
    console.log(`Total Requirements: ${totalReqs}`);
    console.log('');

    // Count by category
    const categoryCounts = {};
    for (const req of generalReqs) {
      categoryCounts[req.category] = (categoryCounts[req.category] || 0) + 1;
    }

    console.log('Requirements by Category:');
    console.log('----------------------------------------');
    const sortedCategories = Object.entries(categoryCounts).sort((a, b) => b[1] - a[1]);
    for (const [category, count] of sortedCategories) {
      console.log(`  ${category.padEnd(30)} ${count}`);
    }
    console.log('');

    // Check for signage
    const signageCount = categoryCounts['signage'] || 0;
    console.log('CRITICAL CHECK: Signage Requirements');
    console.log('----------------------------------------');
    console.log(`  Signage count: ${signageCount}`);
    if (signageCount === 0) {
      console.log('  ✅ PASS: No signage requirements (expected for residential)');
    } else {
      console.log(`  ❌ FAIL: ${signageCount} signage requirements shown (should be 0)`);
    }
    console.log('');

    // Expected reduction
    const expectedBefore = 274; // From database analysis
    const expectedAfter = 180;  // ~40% reduction
    const reductionPercent = ((expectedBefore - totalReqs) / expectedBefore * 100).toFixed(1);

    console.log('FILTERING EFFECTIVENESS:');
    console.log('----------------------------------------');
    console.log(`  Expected before filter: ~${expectedBefore} requirements`);
    console.log(`  Actual after filter: ${totalReqs} requirements`);
    console.log(`  Reduction: ${expectedBefore - totalReqs} requirements (${reductionPercent}%)`);
    console.log(`  Target reduction: ~40%`);

    if (reductionPercent >= 30 && reductionPercent <= 50) {
      console.log('  ✅ PASS: Reduction within expected range');
    } else {
      console.log(`  ⚠️  WARNING: Reduction outside expected range (30-50%)`);
    }
    console.log('');

    // Sample some filtered requirements
    console.log('SAMPLE REQUIREMENTS (first 5):');
    console.log('----------------------------------------');
    for (let i = 0; i < Math.min(5, generalReqs.length); i++) {
      const req = generalReqs[i];
      console.log(`${i+1}. [${req.category}] ${req.requirement_text.substring(0, 70)}...`);
    }

    console.log('\n========================================');
    console.log('TEST COMPLETE');
    console.log('========================================');

  } catch (error) {
    console.error('❌ TEST FAILED');
    console.error('Error:', error.message);
    console.error('');

    if (error.message.includes('ECONNREFUSED')) {
      console.error('Make sure Next.js dev server is running on port 3007');
    }
  }
}

testDevTypeFiltering();
