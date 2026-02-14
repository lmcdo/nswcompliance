import fs from 'fs';

const allFlagged = JSON.parse(fs.readFileSync('./enrichment-FLAGGED-review.json', 'utf-8'));
const mismatchedOnly = allFlagged.filter(p => !p.matched);

console.log(`Filtered to ${mismatchedOnly.length} mismatched provisions (from ${allFlagged.length} total flagged)\n`);

// Save JSON
fs.writeFileSync('./enrichment-MISMATCH-ONLY.json', JSON.stringify(mismatchedOnly, null, 2));

// Create human-readable review file
const reviewOutput = mismatchedOnly.map((r, i) => `
=== MISMATCH ${i + 1}/${mismatchedOnly.length} (ID: ${r.provision_id}) ===
Topic: ${r.v2_topic}

Text:
${r.provision_text.substring(0, 400)}...

Pass 1: ${JSON.stringify(r.pass1_elements)} (conf: ${r.pass1_confidence})
Reasoning: ${r.pass1_reasoning}

Pass 2: ${JSON.stringify(r.pass2_elements)} (conf: ${r.pass2_confidence})
Reasoning: ${r.pass2_reasoning}

✏️  CORRECT TAGS: [ ]
---`).join('\n');

fs.writeFileSync('./enrichment-MISMATCH-ONLY.txt', reviewOutput);

console.log('Created files:');
console.log('  - enrichment-MISMATCH-ONLY.json');
console.log('  - enrichment-MISMATCH-ONLY.txt');
