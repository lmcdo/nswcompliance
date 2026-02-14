import fs from 'fs';
const data = JSON.parse(fs.readFileSync('./gold-standard-llm-tagged.json', 'utf-8'));

const counts = data.reduce((acc, p) => {
  const len = p.elements.length;
  acc[len] = (acc[len] || 0) + 1;
  return acc;
}, {});

console.log('📊 Tagging Summary:\n');
Object.entries(counts).sort((a,b) => a[0]-b[0]).forEach(([count, num]) => {
  const label = count === '0' ? 'Empty []' : count + ' element' + (count > '1' ? 's' : '');
  console.log(`  ${label}: ${num} provisions`);
});

console.log('\n✅ Provisions with elements tagged:');
data.filter(p => p.elements.length > 0).forEach(p => {
  console.log(`  ID ${p.id}: [${p.elements.join(', ')}]`);
  console.log(`    → ${p.text.substring(0, 80)}...`);
});
