#!/usr/bin/env node

/**
 * Search for the "context" definition the user saw
 * "The specific character, quality, physical, historical and social characteristics of a building's setting"
 */

const address = '45 VICTORIA ROAD MARRICKVILLE 2204';
const encodedAddress = encodeURIComponent(address);
const url = `http://localhost:3003/api/provisions/for-property?address=${encodedAddress}&groupBy=toc`;

console.log('🔍 Searching for heritage context definition...\n');

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

  // Search for provisions containing "context" or "setting"
  const contextProvisions = allProvisions.filter(p => {
    const text = p.provision_text?.toLowerCase() || '';
    return (
      text.includes('building\'s setting') ||
      text.includes('buildings setting') ||
      (text.includes('context') && text.includes('suburban street'))
    );
  });

  console.log(`Found ${contextProvisions.length} provisions about context/setting\n`);

  if (contextProvisions.length > 0) {
    console.log('='.repeat(80));
    contextProvisions.forEach((p, idx) => {
      console.log(`\n${idx + 1}. ID: ${p.id}`);
      console.log(`Part: ${p.v2_dcp_part}`);
      console.log(`Section: ${p.section_title || 'N/A'}`);
      console.log(`Topic: ${p.v2_topic}`);
      console.log(`Page: ${p.pdf_page} (printed: ${p.pdf_printed_page})`);
      console.log(`Layer: ${p.v2_dcp_layer}`);
      console.log(`Marker: ${p.v2_marker || 'none'}`);
      console.log(`\nFULL TEXT:`);
      console.log('-'.repeat(80));
      console.log(p.provision_text);
      console.log('-'.repeat(80));

      // Check for AI commentary
      const aiPatterns = [
        'key heritage provision text extracted',
        'key provision text',
        'extracted from this page',
        'based on the image',
      ];

      const foundPatterns = aiPatterns.filter(pattern =>
        p.provision_text?.toLowerCase().includes(pattern.toLowerCase())
      );

      if (foundPatterns.length > 0) {
        console.log(`\n❌ CONTAMINATED! AI patterns found: ${foundPatterns.join(', ')}`);
      }
    });
  } else {
    console.log('No matching provisions found.\n');
    console.log('Trying broader search for "verandah" provisions...\n');

    const verandahProvisions = allProvisions.filter(p =>
      p.v2_topic?.toLowerCase() === 'verandah'
    );

    console.log(`Found ${verandahProvisions.length} verandah provisions:`);
    verandahProvisions.slice(0, 10).forEach((p, idx) => {
      console.log(`\n${idx + 1}. ${p.v2_dcp_part} - Page ${p.pdf_page}`);
      console.log(`   ${p.provision_text?.substring(0, 150)}...`);
    });
  }

} catch (error) {
  console.error('❌ Error:', error.message);
  process.exit(1);
}
