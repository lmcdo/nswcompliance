#!/usr/bin/env node

/**
 * Check what DCP Parts the API is actually returning
 */

const API_BASE = 'http://localhost:3003';

async function checkParts() {
  const url = new URL(`${API_BASE}/api/provisions/for-property`);
  url.searchParams.append('lga', 'Inner West');
  url.searchParams.append('zone', 'R2');
  url.searchParams.append('heritage', 'false');
  url.searchParams.append('former_council', 'leichhardt');
  url.searchParams.append('groupBy', 'toc');  // Get TOC structure

  console.log('🔗 Querying API with groupBy=toc...\n');

  try {
    const response = await fetch(url);
    const data = await response.json();

    if (!data.success) {
      console.log('❌ Error:', data.error);
      return;
    }

    // Check generic layer provisions
    const genericLayer = data.data.by_layer.find(l => l.layer === 'generic');
    console.log(`Generic Layer: ${genericLayer.count} provisions\n`);

    // Group by v2_dcp_part manually
    const byPart = {};
    genericLayer.provisions.forEach(p => {
      const part = p.v2_dcp_part || 'NULL';
      if (!byPart[part]) byPart[part] = 0;
      byPart[part]++;
    });

    console.log('Provisions by v2_dcp_part in Generic Layer:');
    Object.entries(byPart)
      .sort((a, b) => b[1] - a[1])
      .forEach(([part, count]) => {
        console.log(`  ${part.padEnd(40)} ${count}`);
      });

    // Check if Part C Section 1 is present
    const partC1Count = byPart['Part C Section 1'] || 0;
    console.log(`\n🔍 Part C Section 1 provisions: ${partC1Count}`);
    console.log(`   Database has: 1,554`);
    console.log(`   API returned: ${partC1Count}`);

    if (partC1Count === 0) {
      console.log('\n❌ CONFIRMED: Part C Section 1 is being filtered out');
      console.log('   This accounts for 1,554 missing provisions (67% of generic layer)');
    }

    // Check by_toc structure if available
    if (data.data.by_toc) {
      console.log('\n\nTOC Structure:');
      Object.entries(data.data.by_toc).forEach(([partId, part]) => {
        console.log(`\n${partId}: ${part.provision_count} provisions`);
        Object.entries(part.sections).forEach(([sectionId, section]) => {
          console.log(`  Section ${sectionId}: ${section.provision_count}`);
        });
      });
    }

  } catch (error) {
    console.log('❌ Error:', error.message);
  }
}

checkParts();
