#!/usr/bin/env node

/**
 * Check if API is returning provisions with negative pages or TOC type
 */

const address = '45 VICTORIA ROAD MARRICKVILLE 2204';
const encodedAddress = encodeURIComponent(address);
const url = `http://localhost:3003/api/provisions/for-property?address=${encodedAddress}&groupBy=toc`;

console.log('Fetching ALL data from API...\n');

try {
  const response = await fetch(url);
  const data = await response.json();

  if (!data.success) {
    console.error('API Error:', data.error);
    process.exit(1);
  }

  // Collect ALL provisions
  const allProvisions = [];
  const by_toc = data.data?.by_toc || {};

  for (const [partKey, partData] of Object.entries(by_toc)) {
    for (const [secKey, secData] of Object.entries(partData.sections || {})) {
      for (const prov of secData.provisions || []) {
        allProvisions.push({ ...prov, _part: partKey, _section: secKey });
      }
    }
  }

  console.log(`Total provisions fetched: ${allProvisions.length}`);

  // Check for TOC type
  const tocProvisions = allProvisions.filter(p => p.v2_provision_type === 'TOC');
  console.log(`\nProvisions with v2_provision_type='TOC': ${tocProvisions.length}`);

  if (tocProvisions.length > 0) {
    console.log('\n=== TOC PROVISIONS ===');
    tocProvisions.forEach(p => {
      console.log(`ID ${p.id} [${p._part}/${p._section}]`);
      console.log(`  pdf_page: ${p.pdf_page}`);
      console.log(`  pdf_printed_page: ${p.pdf_printed_page}`);
      console.log(`  Text: ${p.provision_text?.substring(0, 80)}...`);
    });
  }

  // Check for negative pdf_page
  const negativePdfPage = allProvisions.filter(p => {
    return p.pdf_page !== null && p.pdf_page !== undefined && p.pdf_page < 0;
  });
  console.log(`\nProvisions with negative pdf_page: ${negativePdfPage.length}`);

  if (negativePdfPage.length > 0) {
    console.log('\n=== NEGATIVE pdf_page ===');
    negativePdfPage.slice(0, 20).forEach(p => {
      console.log(`ID ${p.id} [${p._part}/${p._section}]`);
      console.log(`  pdf_page: ${p.pdf_page}`);
      console.log(`  pdf_printed_page: ${p.pdf_printed_page}`);
      console.log(`  Text: ${p.provision_text?.substring(0, 80)}...`);
    });
  }

  // Check for negative pdf_printed_page
  const negativePrintedPage = allProvisions.filter(p => {
    return p.pdf_printed_page !== null && p.pdf_printed_page !== undefined && p.pdf_printed_page < 0;
  });
  console.log(`\nProvisions with negative pdf_printed_page: ${negativePrintedPage.length}`);

  if (negativePrintedPage.length > 0) {
    console.log('\n=== NEGATIVE pdf_printed_page ===');
    negativePrintedPage.slice(0, 20).forEach(p => {
      console.log(`ID ${p.id} [${p._part}/${p._section}]`);
      console.log(`  pdf_page: ${p.pdf_page}`);
      console.log(`  pdf_printed_page: ${p.pdf_printed_page}`);
      console.log(`  Text: ${p.provision_text?.substring(0, 80)}...`);
    });
  }

  // Check for page -11 specifically
  const page11 = allProvisions.filter(p => p.pdf_page === -11 || p.pdf_printed_page === -11);
  console.log(`\nProvisions with page=-11: ${page11.length}`);

  if (page11.length > 0) {
    console.log('\n=== PAGE -11 PROVISIONS ===');
    page11.forEach(p => {
      console.log(`ID ${p.id} [${p._part}/${p._section}]`);
      console.log(`  pdf_page: ${p.pdf_page}`);
      console.log(`  pdf_printed_page: ${p.pdf_printed_page}`);
      console.log(`  v2_dcp_part: ${p.v2_dcp_part}`);
      console.log(`  Text: ${p.provision_text?.substring(0, 80)}...`);
    });
  }

  // Summary
  console.log('\n=== SUMMARY ===');
  console.log(`Total provisions: ${allProvisions.length}`);
  console.log(`TOC type: ${tocProvisions.length}`);
  console.log(`Negative pdf_page: ${negativePdfPage.length}`);
  console.log(`Negative pdf_printed_page: ${negativePrintedPage.length}`);
  console.log(`Exactly page -11: ${page11.length}`);

  if (tocProvisions.length === 0 && negativePdfPage.length === 0 && negativePrintedPage.length === 0) {
    console.log('\n✅ API IS CLEAN - No TOC or negative pages found!');
    console.log('   Problem must be in frontend component or SWR cache.');
  }

} catch (error) {
  console.error('Error:', error.message);
  process.exit(1);
}
