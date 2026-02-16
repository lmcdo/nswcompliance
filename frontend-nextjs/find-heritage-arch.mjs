#!/usr/bin/env node

// Match what user is seeing: Heritage layer + Archaeological topic
const params = new URLSearchParams({
  address: '45 VICTORIA ROAD MARRICKVILLE 2204',
  groupBy: 'toc',
  former_council: 'Marrickville',
  zone: 'R2',
  heritage: 'true',
  hca: 'Llewellyn Estate Heritage Conservation Area',
  precinct_id: '15_'
});

const url = `http://localhost:3003/api/provisions/for-property?${params.toString()}`;

console.log('🔍 Fetching with heritage filters...\n');
console.log('URL:', url.substring(0, 120) + '...\n');

try {
  const response = await fetch(url);
  const data = await response.json();

  if (!data.success) {
    console.log('❌ API Error:', data.error);
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

  // Filter to archaeological topic
  const archaeological = allProvisions.filter(p =>
    p.v2_topic?.toLowerCase().includes('archaeological')
  );

  console.log(`Archaeological provisions: ${archaeological.length}\n`);

  if (archaeological.length > 0) {
    console.log('='.repeat(80));
    archaeological.forEach((p, idx) => {
      console.log(`\n${idx + 1}. ID: ${p.id}`);
      console.log(`Part: ${p.v2_dcp_part}`);
      console.log(`Topic: ${p.v2_topic}`);
      console.log(`Marker: ${p.v2_marker || 'none'}`);
      console.log(`Page: ${p.pdf_page} | Printed: ${p.pdf_printed_page}`);
      console.log(`\nText (first 200 chars):`);
      console.log(p.provision_text?.substring(0, 200) + '...');
      console.log('-'.repeat(80));
    });

    // Check for duplicates
    if (archaeological.length > 1) {
      console.log('\n' + '='.repeat(80));
      console.log('CHECKING FOR DUPLICATES:\n');

      const textMap = new Map();
      archaeological.forEach(p => {
        // Normalize: strip C1, O1, 01 markers
        const normalized = (p.provision_text || '')
          .replace(/^(C|O)?\d+\s+/gm, '')
          .substring(0, 100)
          .trim();

        const key = `${normalized}|${p.pdf_page || 0}`;

        if (!textMap.has(key)) {
          textMap.set(key, []);
        }
        textMap.get(key).push(p);
      });

      const duplicates = Array.from(textMap.entries()).filter(([_, provisions]) => provisions.length > 1);

      if (duplicates.length > 0) {
        console.log(`❌ Found ${duplicates.length} sets of duplicates!\n`);
        duplicates.forEach(([key, provisions], idx) => {
          console.log(`Duplicate Set ${idx + 1} (${provisions.length} instances):`);
          provisions.forEach((p, i) => {
            console.log(`  ${i + 1}. ID: ${p.id} | Marker: ${p.v2_marker || 'none'} | Page: ${p.pdf_page}`);
          });
          console.log(`  Normalized key: ${key.substring(0, 80)}...`);
          console.log();
        });
      } else {
        console.log('✅ No duplicates found after normalization');
      }
    }
  } else {
    console.log('❌ No archaeological provisions found');
  }

} catch (error) {
  console.error('Error:', error.message);
  process.exit(1);
}
