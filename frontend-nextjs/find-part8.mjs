#!/usr/bin/env node

const address = '45 VICTORIA ROAD MARRICKVILLE 2204';
const url = `http://localhost:3003/api/provisions/for-property?address=${encodeURIComponent(address)}&groupBy=toc`;

try {
  const response = await fetch(url);
  const data = await response.json();
  const by_toc = data.data?.by_toc || {};

  // Find Part 8
  for (const [partKey, partData] of Object.entries(by_toc)) {
    if (partKey.includes('Part 8') || partKey.includes('8')) {
      console.log(`\n=== ${partKey} ===`);
      console.log(`Part page: ${partData.page}`);
      console.log(`Part title: ${partData.title}`);

      const sections = partData.sections || {};
      console.log(`Sections: ${Object.keys(sections).length}`);

      for (const [secKey, secData] of Object.entries(sections)) {
        console.log(`\n  Section: ${secKey}`);
        console.log(`    Title: ${secData.title}`);
        console.log(`    Page: ${secData.page}`);
        console.log(`    Provisions: ${secData.provisions?.length || 0}`);

        if (secData.page && secData.page < 0) {
          console.log(`    ⚠️ NEGATIVE PAGE: ${secData.page}`);
        }

        if (secData.provisions && secData.provisions.length > 0) {
          const prov = secData.provisions[0];
          console.log(`    First provision:`);
          console.log(`      ID: ${prov.id}`);
          console.log(`      pdf_page: ${prov.pdf_page}`);
          console.log(`      pdf_printed_page: ${prov.pdf_printed_page}`);
          console.log(`      v2_provision_type: ${prov.v2_provision_type}`);
          console.log(`      Text: ${prov.provision_text?.substring(0, 80)}...`);
        }
      }
    }
  }
} catch (error) {
  console.error('Error:', error.message);
}
