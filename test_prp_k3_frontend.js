#!/usr/bin/env node
/**
 * Test PRP-K3 Frontend Integration
 * Tests the zone-specific calculation engine through the API
 */

// Use built-in fetch in Node 18+

async function testSetbackCalculation() {
  console.log('=== TESTING PRP-K3 FRONTEND INTEGRATION ===\n');
  
  const testCases = [
    {
      name: 'R2 Residential - Marrickville',
      payload: {
        property_id: 1962876,
        property_zone: 'R2',
        lot_area: 500,
        lot_geometry: {
          hasM: false,
          hasZ: false,
          rings: [[
            [333165.32, 6246431.73],
            [333165.32, 6246451.73],
            [333185.32, 6246451.73],
            [333185.32, 6246431.73],
            [333165.32, 6246431.73]
          ]],
          spatialReference: {
            wkid: 28356,
            latestWkid: 28356
          }
        }
      }
    },
    {
      name: 'R1 Low Density - Ashfield',
      payload: {
        property_id: 1234567,
        property_zone: 'R1',
        lot_area: 800,
        lot_geometry: {
          hasM: false,
          hasZ: false,
          rings: [[
            [333100, 6246400],
            [333100, 6246440],
            [333120, 6246440],
            [333120, 6246400],
            [333100, 6246400]
          ]],
          spatialReference: {
            wkid: 28356,
            latestWkid: 28356
          }
        }
      }
    },
    {
      name: 'B1 Business - Limited Data',
      payload: {
        property_id: 9876543,
        property_zone: 'B1',
        lot_area: 300,
        lot_geometry: {
          hasM: false,
          hasZ: false,
          rings: [[
            [333200, 6246500],
            [333200, 6246515],
            [333220, 6246515],
            [333220, 6246500],
            [333200, 6246500]
          ]],
          spatialReference: {
            wkid: 28356,
            latestWkid: 28356
          }
        }
      }
    }
  ];
  
  for (const testCase of testCases) {
    console.log(`Testing: ${testCase.name}`);
    console.log(`Zone: ${testCase.payload.property_zone}, Property ID: ${testCase.payload.property_id}`);
    
    try {
      const response = await fetch('http://localhost:3007/api/setbacks/calculate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(testCase.payload)
      });
      
      const data = await response.json();
      
      if (data.success) {
        console.log(`✅ SUCCESS - ${data.setback_results.length} setback rules found`);
        console.log(`Processing Method: ${data.processing_method}`);
        console.log(`Processing Time: ${data.processing_time_ms}ms`);
        
        if (data.setback_results.length > 0) {
          console.log('\nSetback Results:');
          data.setback_results.forEach(result => {
            console.log(`  ${result.boundary_type}: ${result.required_setback}m`);
            console.log(`    Authority: ${result.authority} (precedence: ${result.precedence})`);
            console.log(`    Confidence: ${result.confidence}%`);
            console.log(`    Source: ${result.legal_source}`);
          });
        } else {
          console.log('  ⚠️ No setback rules found for this zone');
        }
      } else {
        console.log(`❌ FAILED: ${data.error}`);
      }
    } catch (error) {
      console.log(`❌ ERROR: ${error.message}`);
    }
    
    console.log('-'.repeat(60) + '\n');
  }
  
  // Test database stats endpoint
  console.log('Testing database health check...');
  try {
    const healthResponse = await fetch('http://localhost:3007/api/setbacks/calculate', {
      method: 'GET'
    });
    const health = await healthResponse.json();
    console.log(`Health Status: ${health.status}`);
    if (health.database_stats) {
      console.log('Database Stats:', health.database_stats);
    }
  } catch (error) {
    console.log(`Health check failed: ${error.message}`);
  }
}

// Run the test
testSetbackCalculation().catch(console.error);