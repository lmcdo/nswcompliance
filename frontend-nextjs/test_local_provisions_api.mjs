// Test Planning Portal API for Local Provisions
const propId = 4291806;
const url = `https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/layerintersect?type=property&id=${propId}&layers=epi`;

console.log(`Fetching: ${url}\n`);

const response = await fetch(url, {
  headers: { 'Accept': 'application/json' }
});

if (!response.ok) {
  console.error(`HTTP ${response.status}: ${response.statusText}`);
  process.exit(1);
}

const data = await response.json();

const localProvisionsLayer = data.find(layer => layer.layerName === 'Local Provisions');

if (!localProvisionsLayer) {
  console.log('No Local Provisions layer found');
  process.exit(0);
}

console.log('=== LOCAL PROVISIONS LAYER ===\n');
console.log(JSON.stringify(localProvisionsLayer, null, 2));

console.log('\n=== FIELDS AVAILABLE ===\n');
if (localProvisionsLayer.results && localProvisionsLayer.results[0]) {
  const fields = Object.keys(localProvisionsLayer.results[0]);
  fields.forEach(field => {
    console.log(`  ${field}: ${localProvisionsLayer.results[0][field]}`);
  });
}
