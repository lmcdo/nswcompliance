/**
 * TOD/HIA Integration Test Script
 * Phase 7: Comprehensive testing of TOD detection and display
 *
 * Tests all phases working together:
 * - Phase 1: Timeout protection
 * - Phase 2: Layer detection
 * - Phase 3: TOD layer fetching
 * - Phase 4: Type safety
 * - Phase 5: Constraint extraction
 * - Phase 6: UI data availability
 */

const TEST_ADDRESSES = [
  // TOD Addresses (should have todPrecinct)
  {
    address: '370 Illawarra Rd, Marrickville NSW 2204',
    expectedTOD: true,
    expectedStation: 'Marrickville',
    description: 'Marrickville Station TOD - Primary test case'
  },
  {
    address: '202 Marrickville Rd, Marrickville NSW 2204',
    expectedTOD: true,
    expectedStation: 'Marrickville',
    description: 'Marrickville TOD area'
  },
  {
    address: 'Dulwich Hill Station, NSW 2203',
    expectedTOD: true,
    expectedStation: 'Dulwich Hill',
    description: 'Dulwich Hill Station TOD'
  },

  // Control Addresses (should NOT have todPrecinct)
  {
    address: '14 Hunter St, Lewisham NSW 2049',
    expectedTOD: false,
    description: 'Non-TOD control address'
  },
  {
    address: '3 Wilkinson Ln, Telopea NSW 2117',
    expectedTOD: false,
    description: 'Non-TOD control address (outside Inner West)'
  }
];

// Color codes for terminal output
const GREEN = '\x1b[32m';
const RED = '\x1b[31m';
const YELLOW = '\x1b[33m';
const BLUE = '\x1b[34m';
const RESET = '\x1b[0m';

/**
 * Test a single address
 */
async function testAddress(testCase, apiBaseUrl) {
  console.log(`\n${'='.repeat(80)}`);
  console.log(`${BLUE}Testing: ${testCase.address}${RESET}`);
  console.log(`Description: ${testCase.description}`);
  console.log(`Expected TOD: ${testCase.expectedTOD ? 'YES' : 'NO'}`);

  try {
    const encodedAddress = encodeURIComponent(testCase.address);
    const url = `${apiBaseUrl}/api/property?address=${encodedAddress}`;

    console.log(`\n${YELLOW}Fetching from API...${RESET}`);
    const startTime = Date.now();

    const response = await fetch(url);
    const duration = Date.now() - startTime;

    console.log(`Response time: ${duration}ms`);
    console.log(`Status: ${response.status}`);

    if (!response.ok) {
      console.log(`${RED}✗ FAIL: HTTP ${response.status}${RESET}`);
      return { passed: false, reason: `HTTP ${response.status}` };
    }

    const data = await response.json();

    // Check data structure
    if (!data.success || !data.data) {
      console.log(`${RED}✗ FAIL: Invalid response structure${RESET}`);
      return { passed: false, reason: 'Invalid response structure' };
    }

    const propertyData = data.data;
    const todPrecinct = propertyData.constraints?.todPrecinct;
    const acceleratedTOD = propertyData.constraints?.acceleratedTOD;
    const planningLayers = propertyData.planningLayers || [];

    // Display results
    console.log(`\n${YELLOW}Results:${RESET}`);
    console.log(`  Address: ${propertyData.address}`);
    console.log(`  Zone: ${propertyData.constraints?.zone || 'Unknown'}`);
    console.log(`  LGA: ${propertyData.constraints?.lga || 'Unknown'}`);
    console.log(`  Planning layers received: ${planningLayers.length}`);

    // Check for TOD layers
    const todLayerNames = planningLayers
      .filter(l =>
        l.layerName.toLowerCase().includes('tod') ||
        l.layerName.toLowerCase().includes('transport') ||
        l.layerName.toLowerCase().includes('housing')
      )
      .map(l => l.layerName);

    if (todLayerNames.length > 0) {
      console.log(`  TOD layers found: ${todLayerNames.join(', ')}`);
    } else {
      console.log(`  TOD layers found: None`);
    }

    // Test TOD detection
    console.log(`\n${YELLOW}TOD Detection:${RESET}`);
    console.log(`  TOD precinct present: ${todPrecinct ? 'YES' : 'NO'}`);

    if (todPrecinct) {
      console.log(`  Precinct name: ${todPrecinct.precinctName}`);
      console.log(`  Station name: ${todPrecinct.stationName || 'N/A'}`);
      console.log(`  Station distance: ${todPrecinct.stationDistance ? todPrecinct.stationDistance + 'm' : 'N/A'}`);
      console.log(`  Max FSR: ${todPrecinct.maxFSRBonus || 2.5}:1`);
      console.log(`  Max Height: ${todPrecinct.maxHeightBonus || 24}m`);
      console.log(`  Legislative clause: ${todPrecinct.legislativeClause}`);
      console.log(`  SEPP reference: ${todPrecinct.seppReference}`);
    }

    if (acceleratedTOD) {
      console.log(`  Accelerated TOD: YES`);
      console.log(`  Precinct: ${acceleratedTOD.precinctName}`);
      console.log(`  Expected rezoning: ${acceleratedTOD.expectedRezoning || 'N/A'}`);
    }

    // Validate against expectations
    console.log(`\n${YELLOW}Validation:${RESET}`);

    const hasTOD = !!todPrecinct;
    const todMatch = hasTOD === testCase.expectedTOD;

    if (todMatch) {
      console.log(`  ${GREEN}✓ TOD detection matches expectation${RESET}`);
    } else {
      console.log(`  ${RED}✗ TOD detection mismatch!${RESET}`);
      console.log(`    Expected: ${testCase.expectedTOD}`);
      console.log(`    Got: ${hasTOD}`);
    }

    // Additional validation for TOD addresses
    if (testCase.expectedTOD && hasTOD) {
      // Check station name if expected
      if (testCase.expectedStation) {
        const stationMatch =
          todPrecinct.stationName?.toLowerCase().includes(testCase.expectedStation.toLowerCase()) ||
          todPrecinct.precinctName?.toLowerCase().includes(testCase.expectedStation.toLowerCase());

        if (stationMatch) {
          console.log(`  ${GREEN}✓ Station name matches expectation${RESET}`);
        } else {
          console.log(`  ${YELLOW}⚠ Station name mismatch${RESET}`);
          console.log(`    Expected: ${testCase.expectedStation}`);
          console.log(`    Got: ${todPrecinct.stationName || todPrecinct.precinctName}`);
        }
      }

      // Check for required fields
      const hasRequired =
        todPrecinct.precinctName &&
        todPrecinct.legislativeClause &&
        todPrecinct.seppReference;

      if (hasRequired) {
        console.log(`  ${GREEN}✓ All required fields present${RESET}`);
      } else {
        console.log(`  ${RED}✗ Missing required fields${RESET}`);
      }

      // Check FSR/Height have reasonable values
      const fsrReasonable = todPrecinct.maxFSRBonus >= 1.5 && todPrecinct.maxFSRBonus <= 5;
      const heightReasonable = todPrecinct.maxHeightBonus >= 10 && todPrecinct.maxHeightBonus <= 50;

      if (fsrReasonable && heightReasonable) {
        console.log(`  ${GREEN}✓ FSR/Height values are reasonable${RESET}`);
      } else {
        console.log(`  ${YELLOW}⚠ FSR/Height values may be defaults${RESET}`);
      }
    }

    // Final result
    const passed = todMatch;
    if (passed) {
      console.log(`\n${GREEN}✓ TEST PASSED${RESET}`);
    } else {
      console.log(`\n${RED}✗ TEST FAILED${RESET}`);
    }

    return {
      passed,
      hasTOD,
      todData: todPrecinct,
      duration
    };

  } catch (error) {
    console.log(`\n${RED}✗ ERROR: ${error.message}${RESET}`);
    return { passed: false, error: error.message };
  }
}

/**
 * Run all tests
 */
async function runAllTests() {
  const apiBaseUrl = process.env.API_BASE_URL || 'http://localhost:3000';

  console.log(`${BLUE}${'='.repeat(80)}${RESET}`);
  console.log(`${BLUE}TOD/HIA INTEGRATION TEST SUITE${RESET}`);
  console.log(`${BLUE}Phase 7: End-to-End Testing${RESET}`);
  console.log(`${BLUE}${'='.repeat(80)}${RESET}`);
  console.log(`\nAPI Base URL: ${apiBaseUrl}`);
  console.log(`Total test cases: ${TEST_ADDRESSES.length}`);
  console.log(`  - TOD addresses: ${TEST_ADDRESSES.filter(t => t.expectedTOD).length}`);
  console.log(`  - Control addresses: ${TEST_ADDRESSES.filter(t => !t.expectedTOD).length}`);

  const results = [];

  for (const testCase of TEST_ADDRESSES) {
    const result = await testAddress(testCase, apiBaseUrl);
    results.push({
      address: testCase.address,
      description: testCase.description,
      expectedTOD: testCase.expectedTOD,
      ...result
    });

    // Wait between tests to avoid rate limiting
    await new Promise(resolve => setTimeout(resolve, 2000));
  }

  // Summary
  console.log(`\n\n${BLUE}${'='.repeat(80)}${RESET}`);
  console.log(`${BLUE}TEST SUMMARY${RESET}`);
  console.log(`${BLUE}${'='.repeat(80)}${RESET}`);

  const passed = results.filter(r => r.passed).length;
  const failed = results.filter(r => !r.passed).length;
  const todDetected = results.filter(r => r.hasTOD).length;

  console.log(`\nTotal tests: ${results.length}`);
  console.log(`${GREEN}Passed: ${passed}${RESET}`);
  console.log(`${RED}Failed: ${failed}${RESET}`);
  console.log(`TOD detected: ${todDetected}/${TEST_ADDRESSES.filter(t => t.expectedTOD).length} expected`);

  // Detailed results table
  console.log(`\n${YELLOW}Detailed Results:${RESET}`);
  console.log('─'.repeat(80));
  results.forEach(r => {
    const status = r.passed ? `${GREEN}PASS${RESET}` : `${RED}FAIL${RESET}`;
    const tod = r.hasTOD ? 'YES' : 'NO';
    console.log(`${status} | ${r.address.padEnd(45)} | TOD: ${tod}`);
  });
  console.log('─'.repeat(80));

  // Performance metrics
  const durations = results.filter(r => r.duration).map(r => r.duration);
  if (durations.length > 0) {
    const avgDuration = durations.reduce((a, b) => a + b, 0) / durations.length;
    const maxDuration = Math.max(...durations);
    console.log(`\n${YELLOW}Performance:${RESET}`);
    console.log(`  Average response time: ${Math.round(avgDuration)}ms`);
    console.log(`  Max response time: ${maxDuration}ms`);
    console.log(`  Expected: <10,000ms`);

    if (avgDuration > 10000) {
      console.log(`  ${RED}⚠ Average response time exceeds target${RESET}`);
    } else {
      console.log(`  ${GREEN}✓ Performance within target${RESET}`);
    }
  }

  // Final verdict
  console.log(`\n${BLUE}${'='.repeat(80)}${RESET}`);
  if (failed === 0) {
    console.log(`${GREEN}ALL TESTS PASSED ✓${RESET}`);
    console.log(`\nTOD/HIA integration is working correctly!`);
  } else {
    console.log(`${RED}SOME TESTS FAILED ✗${RESET}`);
    console.log(`\nPlease review failed tests above.`);
  }
  console.log(`${BLUE}${'='.repeat(80)}${RESET}\n`);

  process.exit(failed === 0 ? 0 : 1);
}

// Run tests
runAllTests().catch(error => {
  console.error(`${RED}Fatal error: ${error.message}${RESET}`);
  process.exit(1);
});
