#!/usr/bin/env node

/**
 * Find duplicate Archaeological provisions
 */

const address = '45 VICTORIA ROAD MARRICKVILLE 2204';
const encodedAddress = encodeURIComponent(address);
const url = `http://localhost:3003/api/provisions/for-property?address=${encodedAddress}&groupBy=toc`;

console.log('🔍 Searching for Archaeological heritage provisions...\n');

try {
  const response = await fetch(url);
  const data = await response.json();

  if (!data.success || !data.data?.by_toc) {
    console.log('❌ No provisions found');
    process.exit(1);
  }

  // Collect all provisions
  const allProvisions = [];
  for (const part of Object.values(data.data.by_toc)) {
    for (const section of Object.values(part.sections || {})) {
      allProvisions.push(...(section.provisions || []));
    }
  }

  console.log(`Total provisions: ${allProvisions.length}\n`);

  // Find Archaeological provisions
  const archaeological = allProvisions.filter(p =>
    p.v2_topic?.toLowerCase().includes('archaeological') ||
    p.provision_text?.toLowerCase().includes('archaeological')
  );

  console.log(`Found ${archaeological.length} Archaeological provisions\n`);

  if (archaeological.length > 0) {
    console.log('='.repeat(80));
    archaeological.forEach((p, idx) => {
      console.log(`\n${idx + 1}. ID: ${p.id}`);
      console.log(`Part: ${p.v2_dcp_part}`);
      console.log(`Section: ${p.section_title || 'N/A'}`);
      console.log(`Topic: ${p.v2_topic}`);
      console.log(`Marker: ${p.v2_marker || 'none'}`);
      console.log(`Page: ${p.pdf_page} | Printed: ${p.pdf_printed_page}`);
      console.log(`Layer: ${p.v2_dcp_layer}`);
      console.log(`Priority: ${p.v2_display_priority}`);
      console.log(`\nText (first 300 chars):`);
      console.log('-'.repeat(80));
      console.log(p.provision_text?.substring(0, 300));
      console.log('-'.repeat(80));
    });

    // Check for duplicates by comparing text
    console.log('\n\n' + '='.repeat(80));
    console.log('CHECKING FOR DUPLICATES:\n');

    const textMap = new Map();
    archaeological.forEach(p => {
      // Normalize text for comparison (remove C1/01 prefix variations)
      const normalized = p.provision_text
        ?.replace(/^(C|O)?\d+\s*/gm, '') // Remove C1, O1, 01, etc. prefixes
        .substring(0, 100)
        .toLowerCase()
        .trim();

      if (!normalized) return;

      if (textMap.has(normalized)) {
        textMap.get(normalized).push(p);
      } else {
        textMap.set(normalized, [p]);
      }
    });

    const duplicates = Array.from(textMap.entries()).filter(([_, provisions]) => provisions.length > 1);

    if (duplicates.length > 0) {
      console.log(`❌ Found ${duplicates.length} sets of duplicate provisions!\n`);

      duplicates.forEach(([normalizedText, provisions], idx) => {
        console.log(`\nDuplicate Set ${idx + 1} (${provisions.length} instances):`);
        console.log('-'.repeat(80));
        provisions.forEach((p, i) => {
          console.log(`  ${i + 1}. ID: ${p.id} | Marker: ${p.v2_marker} | Page: ${p.pdf_page}`);
          console.log(`     Text preview: ${p.provision_text?.substring(0, 80)}...`);
        });
      });

      console.log('\n' + '='.repeat(80));
      console.log('💡 RECOMMENDATION:');
      console.log('These duplicates have different marker formats (C1 vs 01) but same content.');
      console.log('The deduplication logic needs to normalize markers before comparing.');
      console.log('='.repeat(80));
    } else {
      console.log('✅ No duplicates found');
    }
  }

} catch (error) {
  console.error('❌ Error:', error.message);
  process.exit(1);
}
