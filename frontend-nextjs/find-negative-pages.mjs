#!/usr/bin/env node

/**
 * Search for provisions with negative or invalid page numbers
 * These are likely data quality issues
 */

const address = '45 VICTORIA ROAD MARRICKVILLE 2204';
const encodedAddress = encodeURIComponent(address);
const url = `http://localhost:3003/api/provisions/for-property?address=${encodedAddress}&groupBy=toc`;

console.log('🔍 Searching for provisions with negative or invalid page numbers...\n');

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

  // Find provisions with negative or invalid pages
  const invalidPages = allProvisions.filter(p => {
    const page = p.pdf_page || p.pdf_printed_page;
    return page < 0 || page === null || page === undefined;
  });

  console.log(`Found ${invalidPages.length} provisions with invalid page numbers\n`);

  if (invalidPages.length > 0) {
    console.log('='.repeat(80));
    console.log('PROVISIONS WITH NEGATIVE/INVALID PAGE NUMBERS:\n');

    invalidPages.slice(0, 20).forEach((p, idx) => {
      console.log(`${idx + 1}. ID: ${p.id} | Page: ${p.pdf_page} | Printed: ${p.pdf_printed_page}`);
      console.log(`   ${p.v2_dcp_part} - ${p.v2_topic}`);
      console.log(`   Topic markers: ${p.v2_marker || 'none'}`);
      console.log(`   Text: ${p.provision_text?.substring(0, 150)}...`);
      console.log();
    });

    if (invalidPages.length > 20) {
      console.log(`... and ${invalidPages.length - 20} more`);
    }
  }

  // Also search for the -9 page specifically
  const page_neg9 = allProvisions.filter(p =>
    p.pdf_page === -9 || p.pdf_printed_page === -9
  );

  if (page_neg9.length > 0) {
    console.log('\n' + '='.repeat(80));
    console.log('PROVISIONS ON PAGE -9 SPECIFICALLY:\n');

    page_neg9.forEach((p, idx) => {
      console.log(`${idx + 1}. ID: ${p.id}`);
      console.log(`   Part: ${p.v2_dcp_part} - Section: ${p.section_title}`);
      console.log(`   Topic: ${p.v2_topic}`);
      console.log(`   Layer: ${p.v2_dcp_layer}`);
      console.log(`\n   FULL TEXT:`);
      console.log('   ' + '-'.repeat(76));
      console.log('   ' + p.provision_text);
      console.log('   ' + '-'.repeat(76));
      console.log();
    });
  }

} catch (error) {
  console.error('❌ Error:', error.message);
  process.exit(1);
}
