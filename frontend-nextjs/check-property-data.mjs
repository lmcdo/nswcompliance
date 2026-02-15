// Check actual property data for invalid numbers
const response = await fetch('http://localhost:3003/api/property-assessment?address=12%20SHELLEYS%20LANE%2C%20PETERSHAM%20NSW%202049');
const data = await response.json();

console.log('=== PROPERTY DATA CHECK ===\n');

// Check lot dimensions
if (data.propertyData?.lotDimensions) {
  console.log('Lot Dimensions:');
  console.log('  area:', data.propertyData.lotDimensions.area);
  console.log('  frontage:', data.propertyData.lotDimensions.frontage);
  console.log('  depth:', data.propertyData.lotDimensions.depth);
  console.log('');
}

// Check planning portal layers
console.log('Planning Portal Layers:');
if (data.propertyData?.planningLayers) {
  data.propertyData.planningLayers.forEach(layer => {
    console.log(`\n${layer.layerName}:`);
    console.log(`  Results count: ${layer.results?.length || 0}`);
    if (layer.results?.[0]) {
      const result = layer.results[0];
      console.log('  Fields:');
      for (const [key, value] of Object.entries(result)) {
        // Check for invalid numbers
        if (typeof value === 'number') {
          if (!isFinite(value) || Math.abs(value) > 1e15) {
            console.log(`    ⚠️  ${key}: ${value} (INVALID NUMBER!)`);
          } else {
            console.log(`    ${key}: ${value}`);
          }
        } else {
          const strVal = String(value);
          if (strVal.length > 50) {
            console.log(`    ${key}: ${strVal.substring(0, 50)}...`);
          } else {
            console.log(`    ${key}: ${strVal}`);
          }
        }
      }
    }
  });
}

// Check for scientific notation anywhere
const jsonStr = JSON.stringify(data);
const scientificMatches = jsonStr.match(/-?\d+\.?\d*e[+-]?\d+/gi);
if (scientificMatches) {
  console.log('\n⚠️  FOUND SCIENTIFIC NOTATION IN DATA:');
  scientificMatches.forEach(match => console.log(`  ${match}`));
}
