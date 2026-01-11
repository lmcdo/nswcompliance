// Test multiple Inner West properties to find all Local Provisions Map Types

const properties = [
  { address: '100 Norton St, Leichhardt', id: 4291806 },
  { address: '1 Westbourne St, Stanmore', id: 2179234 },
  { address: '50 Marion St, Leichhardt', id: 2178824 },
  { address: '100 Australia St, Camperdown', id: 2170523 },
  { address: '200 Parramatta Rd, Stanmore', id: 2179446 }
];

const allLocalProvisions = new Map();

for (const prop of properties) {
  const url = `https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/layerintersect?type=property&id=${prop.id}&layers=epi`;
  
  console.log(`\nFetching: ${prop.address} (ID: ${prop.id})`);
  
  try {
    const response = await fetch(url, { headers: { 'Accept': 'application/json' } });
    
    if (!response.ok) {
      console.log(`  ✗ HTTP ${response.status}`);
      continue;
    }
    
    const data = await response.json();
    const localProvisionsLayer = data.find(layer => layer.layerName === 'Local Provisions');
    
    if (!localProvisionsLayer || !localProvisionsLayer.results || localProvisionsLayer.results.length === 0) {
      console.log(`  - No Local Provisions`);
      continue;
    }
    
    for (const result of localProvisionsLayer.results) {
      const mapType = result['Map Type'];
      const title = result['title'];
      const className = result['Class'];
      
      if (!allLocalProvisions.has(mapType)) {
        allLocalProvisions.set(mapType, {
          mapType,
          title,
          className,
          count: 0
        });
      }
      allLocalProvisions.get(mapType).count++;
      
      console.log(`  ✓ ${mapType}: ${title}`);
    }
  } catch (error) {
    console.log(`  ✗ Error: ${error.message}`);
  }
}

console.log('\n\n=== ALL UNIQUE LOCAL PROVISIONS MAP TYPES ===\n');
console.log(`Found ${allLocalProvisions.size} unique Map Types:\n`);

for (const [mapType, info] of allLocalProvisions.entries()) {
  console.log(`${mapType}:`);
  console.log(`  Title: ${info.title}`);
  console.log(`  Class: ${info.className}`);
  console.log(`  Count: ${info.count} properties\n`);
}
