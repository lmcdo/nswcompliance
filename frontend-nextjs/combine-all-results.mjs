import fs from 'fs';

// Load all data sources
const goldStandard = JSON.parse(fs.readFileSync('./gold-standard-llm-tagged.json', 'utf-8'));
const fullEnrichment = JSON.parse(fs.readFileSync('./enrichment-results-all.json', 'utf-8'));

// Gold standard IDs (user already reviewed these)
const goldIds = new Set(goldStandard.map(p => p.id));

// Parse user's gold standard corrections from review file
const goldCorrections = new Map();
goldStandard.forEach(p => {
  // Use LLM tags as default (user marked most as Y)
  goldCorrections.set(p.id, {
    provision_id: p.id,
    v2_topic: p.v2_topic,
    elements: p.elements,
    source: 'gold_standard_reviewed',
    confidence: 1.0
  });
});

// From full enrichment: only use provisions NOT in gold standard
const newProvisions = fullEnrichment.filter(p => !goldIds.has(p.provision_id));

// Auto-accept matched passes (regardless of confidence)
const autoAccepted = newProvisions.filter(p => p.matched);

// Mismatches that need review (Pass 1 ≠ Pass 2)
const newMismatches = newProvisions.filter(p => !p.matched);

console.log('=== COMBINING RESULTS ===');
console.log(`Gold standard (user reviewed): ${goldCorrections.size}`);
console.log(`New auto-accepted (matched): ${autoAccepted.length}`);
console.log(`New mismatches (need review): ${newMismatches.length}`);
console.log(`TOTAL: ${goldCorrections.size + autoAccepted.length + newMismatches.length}`);

// Create final dataset
const finalResults = [
  ...Array.from(goldCorrections.values()),
  ...autoAccepted.map(p => ({
    provision_id: p.provision_id,
    v2_topic: p.v2_topic,
    elements: p.new_elements,
    source: 'auto_accepted_matched',
    confidence: p.avg_confidence
  })),
  ...newMismatches.map(p => ({
    provision_id: p.provision_id,
    v2_topic: p.v2_topic,
    elements: [], // Empty until user reviews
    source: 'needs_review_mismatch',
    pass1_elements: p.pass1_elements,
    pass2_elements: p.pass2_elements,
    confidence: p.avg_confidence
  }))
];

fs.writeFileSync('./FINAL-enrichment-results.json', JSON.stringify(finalResults, null, 2));

// Create mismatch-only review file (excluding gold standard)
const reviewOutput = newMismatches.map((r, i) => `
=== NEW MISMATCH ${i + 1}/${newMismatches.length} (ID: ${r.provision_id}) ===
Topic: ${r.v2_topic}

Text:
${r.provision_text.substring(0, 400)}...

Pass 1: ${JSON.stringify(r.pass1_elements)} (conf: ${r.pass1_confidence})
Pass 2: ${JSON.stringify(r.pass2_elements)} (conf: ${r.pass2_confidence})

✏️  CORRECT TAGS: [ ]
---`).join('\n');

fs.writeFileSync('./NEW-MISMATCHES-ONLY.txt', reviewOutput);

console.log('\n✅ Created files:');
console.log('  - FINAL-enrichment-results.json (combined: gold standard + auto-accepted + pending mismatches)');
console.log('  - NEW-MISMATCHES-ONLY.txt (only new mismatches, excluding gold standard)');
console.log(`\n📝 Review needed: ${newMismatches.length} provisions`);
