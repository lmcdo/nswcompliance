// Test both geometry formats to ensure no hardcoding
console.log("Testing Standard ESRI Format:");

const standardFormat = {
  property_id: 123,
  lot_geometry: {
    hasM: false,
    hasZ: false,
    rings: [
      // Standard ESRI format: rings[0] = [[x,y], [x,y]...]
      [
        [151.1, -33.9, 0],
        [151.2, -33.9, 0],
        [151.2, -33.8, 0],
        [151.1, -33.8, 0],
        [151.1, -33.9, 0]
      ]
    ],
    spatialReference: { wkid: 4326 }
  },
  property_zone: "R1",
  lot_area: 450
};

const nswFormat = {
  property_id: 124,
  lot_geometry: {
    hasM: false,
    hasZ: false,
    rings: [
      // NSW API format: rings[0][0] = [[x,y], [x,y]...]
      [
        [
          [151.1, -33.9, 0],
          [151.2, -33.9, 0],
          [151.2, -33.8, 0],
          [151.1, -33.8, 0],
          [151.1, -33.9, 0]
        ]
      ]
    ],
    spatialReference: { wkid: 4326 }
  },
  property_zone: "R1", 
  lot_area: 450
};

async function testFormat(name, data) {
  console.log(`\n=== Testing ${name} ===`);
  try {
    const response = await fetch('http://localhost:3002/api/setbacks/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    
    const result = await response.json();
    
    if (result.success) {
      console.log(`✅ ${name} SUCCESS - ${result.setback_results.length} setbacks found`);
      console.log(`   Processing: ${result.processing_time_ms}ms`);
    } else {
      console.log(`❌ ${name} FAILED:`, result.error);
    }
  } catch (error) {
    console.log(`❌ ${name} ERROR:`, error.message);
  }
}

// Test both formats
Promise.all([
  testFormat("Standard ESRI Format", standardFormat),
  testFormat("NSW API Format", nswFormat)
]).then(() => {
  console.log("\n=== Format Flexibility Test Complete ===");
});