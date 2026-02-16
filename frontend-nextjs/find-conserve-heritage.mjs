#!/usr/bin/env node

/**
 * Search for "To conserve heritage items" objectives
 */

const address = '45 VICTORIA ROAD MARRICKVILLE 2204';
const encodedAddress = encodeURIComponent(address);
const url = `http://localhost:3003/api/provisions/for-property?address=${encodedAddress}&groupBy=toc`;

console.log('🔍 Searching for "To conserve heritage items" provisions...\n');

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

  // Find provisions containing "To conserve heritage"
  const matches = allProvisions.filter(p =>
    p.provision_text?.includes('To conserve heritage items')
  );

  console.log(`Found ${matches.length} matching provisions\n`);

  if (matches.length > 0) {
    console.log('='.repeat(80));
    matches.forEach((p, idx) => {
      console.log(`\n${idx + 1}. ID: ${p.id}`);
      console.log(`Part: ${p.v2_dcp_part}`);
      console.log(`Section: ${p.section_title || 'N/A'}`);
      console.log(`Topic: ${p.v2_topic}`);
      console.log(`Marker: ${p.v2_marker || 'none'}`);
      console.log(`Page: ${p.pdf_page} | Printed: ${p.pdf_printed_page}`);
      console.log(`Layer: ${p.v2_dcp_layer}`);
      console.log(`Priority: ${p.v2_display_priority}`);
      console.log(`Provision type: ${p.v2_provision_type}`);
      console.log(`\nFULL TEXT:`);
      console.log('-'.repeat(80));
      console.log(p.provision_text);
      console.log('-'.repeat(80));
    });

    // Check for duplicates
    if (matches.length > 1) {
      console.log('\n' + '='.repeat(80));
      console.log('⚠️  MULTIPLE INSTANCES FOUND!');
      console.log('='.repeat(80));
      console.log('\nComparing text to identify duplicates:\n');

      for (let i = 0; i < matches.length; i++) {
        for (let j = i + 1; j < matches.length; j++) {
          const p1 = matches[i];
          const p2 = matches[j];

          // Normalize both texts (remove C/O prefixes)
          const normalize = (text) => text
            ?.replace(/^(C|O)?\d+\s*/gm, '')
            .replace(/^\d+\s*/gm, '')
            .trim();

          const norm1 = normalize(p1.provision_text);
          const norm2 = normalize(p2.provision_text);

          if (norm1 === norm2) {
            console.log(`❌ EXACT DUPLICATE: ID ${p1.id} and ID ${p2.id}`);
            console.log(`   Both have identical text after normalization`);
            console.log(`   p1 marker: ${p1.v2_marker}, page: ${p1.pdf_page}`);
            console.log(`   p2 marker: ${p2.v2_marker}, page: ${p2.pdf_page}\n`);
          }
        }
      }
    }
  } else {
    console.log('No matches found. Trying broader search...\n');

    // Search for any heritage objectives
    const heritage = allProvisions.filter(p =>
      p.v2_marker?.startsWith('O') &&
      (p.v2_topic?.toLowerCase().includes('heritage') || p.provision_text?.toLowerCase().includes('heritage'))
    );

    console.log(`Found ${heritage.length} heritage objectives (O markers):`);
    heritage.slice(0, 10).forEach((p, idx) => {
      console.log(`\n${idx + 1}. ID: ${p.id} | ${p.v2_dcp_part} - ${p.v2_topic}`);
      console.log(`   Marker: ${p.v2_marker} | Page: ${p.pdf_page}`);
      console.log(`   ${p.provision_text?.substring(0, 100)}...`);
    });
  }

} catch (error) {
  console.error('❌ Error:', error.message);
  process.exit(1);
}
