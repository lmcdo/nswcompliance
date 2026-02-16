#!/usr/bin/env node

const address = '45 VICTORIA ROAD MARRICKVILLE 2204';
const encodedAddress = encodeURIComponent(address);
const url = `http://localhost:3003/api/provisions/for-property?address=${encodedAddress}&groupBy=toc`;

console.log('🔍 Searching for "To retain evidence" provisions...\n');

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

  // Find provisions containing "To retain evidence"
  const matches = allProvisions.filter(p =>
    p.provision_text?.includes('To retain evidence')
  );

  console.log(`Found ${matches.length} matching provisions\n`);

  if (matches.length > 0) {
    console.log('='.repeat(80));
    matches.forEach((p, idx) => {
      console.log(`\n${idx + 1}. ID: ${p.id}`);
      console.log(`Part: ${p.v2_dcp_part}`);
      console.log(`Topic: ${p.v2_topic}`);
      console.log(`Marker: ${p.v2_marker || 'none'}`);
      console.log(`Page: ${p.pdf_page} | Printed: ${p.pdf_printed_page}`);
      console.log(`Layer: ${p.v2_dcp_layer}`);
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

          // Normalize both texts (remove C/O prefixes from line starts)
          const normalize = (text) => text
            ?.replace(/^(C|O)?\d+\s+/gm, '')  // Strip C1, O1, 01 from line starts
            .trim();

          const norm1 = normalize(p1.provision_text);
          const norm2 = normalize(p2.provision_text);

          console.log(`Comparing ID ${p1.id} vs ID ${p2.id}:`);
          console.log(`  Same page? ${p1.pdf_page === p2.pdf_page}`);
          console.log(`  Normalized text match? ${norm1 === norm2}`);

          if (norm1 === norm2) {
            console.log(`  ❌ EXACT DUPLICATE after normalization`);
          } else {
            console.log(`  ℹ️  Different text (first 100 chars):`);
            console.log(`     p1: ${norm1.substring(0, 100)}...`);
            console.log(`     p2: ${norm2.substring(0, 100)}...`);
          }
          console.log();
        }
      }
    }
  }

} catch (error) {
  console.error('❌ Error:', error.message);
  process.exit(1);
}
