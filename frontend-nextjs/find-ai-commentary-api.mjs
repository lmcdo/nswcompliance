#!/usr/bin/env node

/**
 * Find AI-generated commentary contaminating provision text
 * Uses the API to search provisions
 */

// Test addresses that should return provisions
const TEST_ADDRESSES = [
  '45 VICTORIA ROAD MARRICKVILLE 2204', // Heritage property with provisions
  '12 SHELLEYS LANE PETERSHAM 2049',
  '1 Railway PARADE MARRICKVILLE 2204'
];

const AI_PATTERNS = [
  'key heritage provision text extracted from this page',
  'key provision text extracted',
  'extracted from this page is:',
  'based on the image',
  'the document specifies',
];

async function searchProvisionsForPattern(pattern) {
  console.log(`\nSearching for pattern: "${pattern}"`);
  const contaminated = [];

  for (const address of TEST_ADDRESSES) {
    const encodedAddress = encodeURIComponent(address);
    const url = `http://localhost:3003/api/provisions/for-property?address=${encodedAddress}&groupBy=toc`;

    try {
      const response = await fetch(url);
      const data = await response.json();

      if (!data.success || !data.data?.by_toc) {
        console.log(`  ⚠️  No provisions found for ${address}`);
        continue;
      }

      // Search through all provisions
      const provisions = [];
      for (const part of Object.values(data.data.by_toc)) {
        for (const section of Object.values(part.sections || {})) {
          provisions.push(...(section.provisions || []));
        }
      }

      // Check each provision for the pattern
      const matches = provisions.filter(p =>
        p.provision_text?.toLowerCase().includes(pattern.toLowerCase())
      );

      if (matches.length > 0) {
        console.log(`  ❌ Found ${matches.length} contaminated provisions for ${address}`);
        contaminated.push(...matches.map(m => ({
          ...m,
          pattern,
          address
        })));
      }
    } catch (error) {
      console.error(`  Error querying ${address}:`, error.message);
    }
  }

  return contaminated;
}

async function main() {
  console.log('🔍 Searching for AI commentary in provision_text...');
  console.log('Using API endpoint to query provisions\n');

  const allContaminated = [];

  for (const pattern of AI_PATTERNS) {
    const results = await searchProvisionsForPattern(pattern);
    allContaminated.push(...results);
  }

  console.log('\n' + '='.repeat(80));
  console.log(`TOTAL CONTAMINATED PROVISIONS FOUND: ${allContaminated.length}`);
  console.log('='.repeat(80));

  if (allContaminated.length > 0) {
    console.log('\n📋 SAMPLE CONTAMINATED PROVISIONS:\n');

    const unique = Array.from(new Map(allContaminated.map(p => [p.id, p])).values());

    unique.slice(0, 10).forEach((p, idx) => {
      console.log(`\n${idx + 1}. ID: ${p.id}`);
      console.log(`   Address: ${p.address}`);
      console.log(`   Pattern: "${p.pattern}"`);
      console.log(`   Council: ${p.former_council} | Part: ${p.v2_dcp_part} | Topic: ${p.v2_topic}`);
      console.log(`   Page: ${p.pdf_page}`);
      console.log(`   Text: ${p.provision_text?.substring(0, 200)}...`);
      console.log('   ' + '-'.repeat(76));
    });

    if (unique.length > 10) {
      console.log(`\n   ... and ${unique.length - 10} more unique contaminated provisions`);
    }

    console.log('\n' + '='.repeat(80));
    console.log('💡 ACTION REQUIRED:');
    console.log('These provisions contain AI-generated commentary/framing text.');
    console.log('The provision_text should contain ONLY the actual DCP text.');
    console.log('This data needs to be cleaned or re-extracted properly.');
    console.log('='.repeat(80));
  } else {
    console.log('\n✅ No AI commentary found in sample provisions!');
    console.log('Note: This search only covers provisions from test addresses.');
    console.log('A full database scan would be needed for complete verification.');
  }
}

main().catch(console.error);
