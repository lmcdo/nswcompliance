#!/usr/bin/env node
/**
 * Test TOC structure for all 3 former councils
 * Verifies groupBy=toc parameter returns proper DCP part/section structure
 */

async function testTocStructure(formerCouncil) {
  const params = new URLSearchParams({
    lga: 'Inner West',
    zone: 'R2',
    heritage: 'false',
    former_council: formerCouncil,
    groupBy: 'toc'
  });

  try {
    const response = await fetch(`http://localhost:3003/api/provisions/for-property?${params}`);
    const data = await response.json();

    console.log(`\n${'='.repeat(60)}`);
    console.log(`${formerCouncil.toUpperCase()} TOC STRUCTURE`);
    console.log('='.repeat(60));

    // Response structure is { success: true, data: { by_toc: {...}, by_layer: [...] } }
    const tocData = data.data?.by_toc;
    const layerData = data.data?.by_layer;
    const summary = data.data?.summary;

    console.log('Success:', data.success);
    console.log('Has by_toc:', !!tocData);
    console.log('Total provisions (from summary):', summary?.total_provisions || 0);

    if (tocData && Object.keys(tocData).length > 0) {
      const parts = Object.keys(tocData);
      console.log('TOC Parts:', parts.length);
      console.log();

      // Show first 5 parts
      parts.slice(0, 5).forEach(part => {
        const partData = tocData[part];
        const sections = Object.keys(partData.sections);
        console.log(`  ${partData.part_name || part}: ${sections.length} sections, ${partData.provision_count} provisions`);

        // Show first 3 sections
        sections.slice(0, 3).forEach(sectionId => {
          const section = partData.sections[sectionId];
          console.log(`    - ${section.section_title}: ${section.provision_count} provisions`);
        });

        if (sections.length > 3) {
          console.log(`    ... and ${sections.length - 3} more sections`);
        }
        console.log();
      });

      if (parts.length > 5) {
        console.log(`  ... and ${parts.length - 5} more parts`);
      }
    } else {
      console.log('⚠️  No TOC structure returned');
    }

    return {
      council: formerCouncil,
      hasToc: !!tocData && Object.keys(tocData).length > 0,
      parts: tocData ? Object.keys(tocData).length : 0,
      totalProvisions: summary?.total_provisions || 0
    };
  } catch (error) {
    console.error(`Error testing ${formerCouncil}:`, error.message);
    return {
      council: formerCouncil,
      error: error.message
    };
  }
}

async function main() {
  console.log('Testing TOC Structure for All 3 Former Councils');
  console.log('================================================\n');

  const councils = ['leichhardt', 'marrickville', 'ashfield'];
  const results = [];

  for (const council of councils) {
    const result = await testTocStructure(council);
    results.push(result);
  }

  console.log('\n' + '='.repeat(60));
  console.log('SUMMARY');
  console.log('='.repeat(60));

  results.forEach(r => {
    if (r.error) {
      console.log(`${r.council}: ❌ ERROR - ${r.error}`);
    } else if (r.hasToc) {
      console.log(`${r.council}: ✓ ${r.parts} parts, ${r.totalProvisions} provisions`);
    } else {
      console.log(`${r.council}: ⚠️  No TOC structure`);
    }
  });

  const allHaveToc = results.every(r => !r.error && r.hasToc);
  console.log();
  if (allHaveToc) {
    console.log('✅ All 3 councils have TOC structure working correctly');
  } else {
    console.log('⚠️  Some councils missing TOC structure');
  }
}

main().catch(console.error);
