#!/usr/bin/env node

const address = '45 VICTORIA ROAD MARRICKVILLE 2204';
const url = `http://localhost:3003/api/provisions/for-property?address=${encodeURIComponent(address)}&groupBy=toc`;

try {
  const response = await fetch(url);
  const data = await response.json();
  const by_toc = data.data?.by_toc || {};

  console.log('Searching for negative page numbers in TOC structure...\n');

  let foundNegative = false;

  for (const [partKey, partData] of Object.entries(by_toc)) {
    const sections = partData.sections || {};

    for (const [secKey, secData] of Object.entries(sections)) {
      // Check section page
      if (secData.page && secData.page < 0) {
        console.log(`❌ NEGATIVE in section: ${partKey} / ${secKey}`);
        console.log(`   Section page: ${secData.page}`);
        console.log(`   Provisions: ${secData.provisions?.length || 0}`);
        foundNegative = true;
      }

      // Check provision pages
      if (secData.provisions) {
        for (const prov of secData.provisions) {
          const page = prov.pdf_page ?? prov.pdf_printed_page;
          if (page !== null && page !== undefined && page < 0) {
            console.log(`❌ NEGATIVE in provision: ${partKey} / ${secKey}`);
            console.log(`   Provision ID: ${prov.id}`);
            console.log(`   pdf_page: ${prov.pdf_page}`);
            console.log(`   pdf_printed_page: ${prov.pdf_printed_page}`);
            console.log(`   Text: ${prov.provision_text?.substring(0, 80)}...`);
            foundNegative = true;
          }
        }
      }
    }
  }

  if (!foundNegative) {
    console.log('✅ No negative page numbers found in API response');
  }

  // Also check complete_toc if it exists
  const complete_toc = data.data?.complete_toc;
  if (complete_toc) {
    console.log('\n\nChecking complete_toc structure...');
    console.log(JSON.stringify(complete_toc, null, 2).substring(0, 2000));
  }
} catch (error) {
  console.error('Error:', error.message);
}
