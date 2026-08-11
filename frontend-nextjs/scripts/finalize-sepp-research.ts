#!/usr/bin/env tsx
/**
 * Finalize SEPP Research
 *
 * Updates research JSON with all automated browser findings
 */

import * as fs from 'fs';
import * as path from 'path';

const allFindings = {
  'sepp-transport-infrastructure-2021': {
    dates: ['20/06/2025', '11/07/2025', '15/08/2025', '14/11/2025', '12/12/2025'],
    hasAmendments: true
  },
  'sepp-exempt-complying-codes-2008': {
    dates: ['29/08/2025', '26/09/2025', '31/10/2025', '14/11/2025', '12/12/2025'],
    hasAmendments: true
  },
  'sepp-planning-systems-2021': {
    dates: ['17/10/2025', '12/12/2025', '16/01/2026'], // sorted
    hasAmendments: true
  },
  'sepp-industry-employment-2021': {
    dates: ['17/10/2025', '07/11/2025'], // sorted
    hasAmendments: true
  },
  'sepp-biodiversity-conservation-2021': {
    dates: [],
    hasAmendments: false
  },
  'sepp-resilience-hazards-2021': {
    dates: [],
    hasAmendments: false
  },
  'sepp-primary-production-2021': {
    dates: [],
    hasAmendments: false
  },
  'sepp-sustainable-buildings-2022': {
    dates: [],
    hasAmendments: false
  }
};

function convertDate(ddmmyyyy: string): string {
  const [dd, mm, yyyy] = ddmmyyyy.split('/');
  return `${yyyy}-${mm}-${dd}`;
}

async function finalizeResearch() {
  const researchPath = path.join(__dirname, 'sepp-amendments-research.json');
  const research = JSON.parse(fs.readFileSync(researchPath, 'utf8'));

  console.log('=== Finalizing SEPP Research ===\n');

  let updated = 0;
  let noAmendments = 0;

  for (const sepp of research.sepps) {
    if (sepp.slug === 'sepp-housing-2021') {
      console.log(`✅ ${sepp.name}: Already researched (5 amendments)`);
      continue;
    }

    const findings = allFindings[sepp.slug as keyof typeof allFindings];
    if (!findings) continue;

    if (findings.hasAmendments && findings.dates.length > 0) {
      sepp.amendments_found = findings.dates.map((date, idx) => ({
        epi: `TBD-${idx + 1}/${date.split('/')[2]}`,
        effective_date: convertDate(date),
        description: `Version consolidated ${date} (EPI number requires manual verification from NSW Legislation historical notes)`,
        affects_provisions: true,
        note: 'Auto-detected from point-in-time versions. Manual verification needed for exact EPI numbers and change descriptions.'
      }));
      sepp.research_notes = `Automated browser research found ${findings.dates.length} consolidation dates after Oct 14, 2025. Point-in-time versions available on NSW Legislation. EPI numbers need manual verification.`;
      sepp.researcher = 'Automated (browser + Claude)';
      sepp.status = 'NEEDS_MANUAL_VERIFICATION';

      console.log(`✅ ${sepp.name}: ${findings.dates.length} versions found`);
      updated++;
    } else {
      sepp.amendments_found = [];
      sepp.research_notes = 'Automated browser research found NO amendments or new consolidations after Oct 14, 2025. SEPP appears stable.';
      sepp.researcher = 'Automated (browser + Claude)';
      sepp.status = 'VERIFIED_NO_AMENDMENTS';
      sepp.research_date = '2026-02-20';

      console.log(`ℹ️  ${sepp.name}: No amendments`);
      noAmendments++;
    }
  }

  fs.writeFileSync(researchPath, JSON.stringify(research, null, 2));

  console.log('\n=== Summary ===');
  console.log(`SEPPs with amendments: ${updated + 1} (including Housing)`);
  console.log(`SEPPs with NO amendments: ${noAmendments}`);
  console.log(`\nBreakdown:`);
  console.log(`  Housing: 5 amendments (fully researched)`);
  console.log(`  Transport: 5 versions`);
  console.log(`  Exempt & Complying: 5 versions`);
  console.log(`  Planning Systems: 3 versions`);
  console.log(`  Industry & Employment: 2 versions`);
  console.log(`  Biodiversity: None`);
  console.log(`  Resilience: None`);
  console.log(`  Primary Production: None`);
  console.log(`  Sustainable Buildings: None`);

  console.log('\n✅ Research JSON updated: sepp-amendments-research.json');
  console.log('\n=== Next Step ===');
  console.log('Run: npm exec tsx scripts/apply-sepp-amendments.ts');
}

finalizeResearch();
