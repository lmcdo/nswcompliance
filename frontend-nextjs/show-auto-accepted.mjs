import fs from 'fs';

const data = JSON.parse(fs.readFileSync('./enrichment-results-all.json', 'utf-8'));
const autoAccepted = data.filter(p => !p.needs_review).slice(0, 10);

console.log('=== AUTO-ACCEPTED EXAMPLES ===\n');
autoAccepted.forEach((p, i) => {
  console.log(`${i+1}. ID ${p.provision_id} (${p.v2_topic}): ${JSON.stringify(p.new_elements)}`);
  console.log(`   Text: ${p.provision_text.substring(0, 120)}...`);
  console.log(`   Confidence: ${p.avg_confidence}\n`);
});

console.log('\n=== STATISTICS ===');
const withElements = data.filter(p => p.new_elements && p.new_elements.length > 0);
const emptyElements = data.filter(p => !p.new_elements || p.new_elements.length === 0);
const elementCounts = data.reduce((acc, p) => {
  const len = (p.new_elements || []).length;
  acc[len] = (acc[len] || 0) + 1;
  return acc;
}, {});

console.log(`Total provisions: ${data.length}`);
console.log(`With elements: ${withElements.length} (${(withElements.length/data.length*100).toFixed(1)}%)`);
console.log(`Empty []: ${emptyElements.length} (${(emptyElements.length/data.length*100).toFixed(1)}%)`);
console.log(`\nElement count distribution:`);
Object.entries(elementCounts).sort((a,b) => Number(a[0]) - Number(b[0])).forEach(([count, num]) => {
  const label = count === '0' ? 'Empty []' : count + ' element' + (count > '1' ? 's' : '');
  console.log(`  ${label}: ${num} provisions`);
});
