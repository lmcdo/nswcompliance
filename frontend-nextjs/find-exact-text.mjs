#!/usr/bin/env node

/**
 * Search for the exact contaminated provision the user saw
 */

const EXACT_TEXT = "The specific character, quality, physical, historical and social characteristics of a building's setting";

// Try the address from the user's screenshot
const address = '45 VICTORIA ROAD MARRICKVILLE 2204';
const encodedAddress = encodeURIComponent(address);
const url = `http://localhost:3003/api/provisions/for-property?address=${encodedAddress}&groupBy=toc`;

console.log('🔍 Searching for exact provision text...\n');
console.log(`Address: ${address}`);
console.log(`Looking for: "${EXACT_TEXT}"\n`);

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

  console.log(`Total provisions fetched: ${allProvisions.length}\n`);

  // Search for the exact text
  const matches = allProvisions.filter(p =>
    p.provision_text?.includes(EXACT_TEXT)
  );

  if (matches.length > 0) {
    console.log(`✅ FOUND ${matches.length} MATCHING PROVISION(S)!\n`);
    console.log('='.repeat(80));

    matches.forEach((p, idx) => {
      console.log(`\nProvision ${idx + 1}:`);
      console.log(`ID: ${p.id}`);
      console.log(`Council: ${p.former_council}`);
      console.log(`Part: ${p.v2_dcp_part}`);
      console.log(`Section: ${p.section_title || 'N/A'}`);
      console.log(`Topic: ${p.v2_topic}`);
      console.log(`Layer: ${p.v2_dcp_layer}`);
      console.log(`Page: ${p.pdf_page}`);
      console.log(`\nFULL TEXT:`);
      console.log('-'.repeat(80));
      console.log(p.provision_text);
      console.log('-'.repeat(80));
    });

    // Search for AI commentary patterns in this provision
    const aiPatterns = [
      'key heritage provision text extracted',
      'key provision text',
      'extracted from this page',
      'based on the image',
    ];

    console.log('\n' + '='.repeat(80));
    console.log('🔍 CHECKING FOR AI COMMENTARY PATTERNS:\n');

    matches.forEach(p => {
      const found = aiPatterns.filter(pattern =>
        p.provision_text?.toLowerCase().includes(pattern.toLowerCase())
      );

      if (found.length > 0) {
        console.log(`❌ CONTAMINATED! Found patterns: ${found.join(', ')}`);
      } else {
        console.log(`✅ No AI commentary patterns detected`);
        console.log(`   (But the text might still be a definition rather than a provision)`);
      }
    });

  } else {
    console.log('❌ No matching provisions found');
    console.log('\nSearching for partial matches...\n');

    // Try partial search
    const partial = allProvisions.filter(p =>
      p.provision_text?.includes("specific character") ||
      p.provision_text?.includes("building's setting")
    );

    if (partial.length > 0) {
      console.log(`Found ${partial.length} provisions with partial matches:`);
      partial.slice(0, 5).forEach((p, idx) => {
        console.log(`\n${idx + 1}. ${p.v2_dcp_part} - ${p.v2_topic} (Page ${p.pdf_page})`);
        console.log(`   ${p.provision_text?.substring(0, 200)}...`);
      });
    }
  }

} catch (error) {
  console.error('❌ Error:', error.message);
  process.exit(1);
}
