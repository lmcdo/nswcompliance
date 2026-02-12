import fs from 'fs';
const data = JSON.parse(fs.readFileSync('C:\Users\lawre\Downloads\cardigan-test-correct.json', 'utf8'));

console.log('=== 33 CARDIGAN ST WITH CORRECT PARAMS ===\n');

console.log('LAYER BREAKDOWN:');
data.data.by_layer.forEach(layer => {
  console.log(`  ${layer.layer_name} (${layer.layer}): ${layer.count} provisions`);
});

console.log(`\nTOTAL: ${data.data.summary.total_provisions} provisions`);

// Heritage topics
console.log('\n=== HERITAGE-TAGGED PROVISIONS BY TOPIC ===');
const topics = {};
data.data.by_layer.forEach(layer => {
  layer.provisions.forEach(p => {
    if (p.v2_marker === 'heritage') {
      const topic = p.v2_topic || 'unknown';
      topics[topic] = (topics[topic] || 0) + 1;
    }
  });
});

Object.entries(topics)
  .sort((a,b) => b[1] - a[1])
  .forEach(([topic, count]) => {
    console.log(`  ${topic}: ${count}`);
  });

console.log(`\nTOTAL HERITAGE: ${Object.values(topics).reduce((a,b) => a+b, 0)}`);

// Precinct check
const precinctLayer = data.data.by_layer.find(l => l.layer === 'precinct');
console.log('\n=== PRECINCT LAYER (Layer 4) ===');
console.log(`Count: ${precinctLayer.count}`);
if (precinctLayer.count > 0) {
  console.log('\nSample precinct provisions:');
  precinctLayer.provisions.slice(0, 3).forEach((p, i) => {
    console.log(`\n${i+1}. v2_precinct_id: ${p.v2_precinct_id}`);
    console.log(`   Topic: ${p.v2_topic}`);
    console.log(`   Text: ${p.provision_text.substring(0, 80)}...`);
  });
}
