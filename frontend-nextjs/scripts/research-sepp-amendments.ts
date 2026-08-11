#!/usr/bin/env tsx
/**
 * Research SEPP Amendments from NSW Legislation
 *
 * This script provides a structured workflow to research and document
 * SEPP amendments from the NSW Legislation website.
 */

import { getPool } from '@/lib/database/pool-manager';

const pool = getPool();

// Main SEPPs to research
const sepps = [
  {
    name: 'Housing SEPP 2021',
    slug: 'sepp-housing-2021',
    epi_number: '2021-0714',
    url: 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714',
    pdf_name_pattern: '%Housing%2021%',
    last_verified: '2025-10-14'
  },
  {
    name: 'Transport & Infrastructure SEPP 2021',
    slug: 'sepp-transport-infrastructure-2021',
    epi_number: '2021-0732',
    url: 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0732',
    pdf_name_pattern: '%Transport%Infrastructure%2021%',
    last_verified: '2025-10-14'
  },
  {
    name: 'Biodiversity & Conservation SEPP 2021',
    slug: 'sepp-biodiversity-conservation-2021',
    epi_number: '2021-0722',
    url: 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0722',
    pdf_name_pattern: '%Biodiversity%Conservation%2021%',
    last_verified: '2025-10-14'
  },
  {
    name: 'Resilience & Hazards SEPP 2021',
    slug: 'sepp-resilience-hazards-2021',
    epi_number: '2021-0730',
    url: 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0730',
    pdf_name_pattern: '%Resilience%Hazards%2021%',
    last_verified: '2025-10-14'
  },
  {
    name: 'Planning Systems SEPP 2021',
    slug: 'sepp-planning-systems-2021',
    epi_number: '2021-0728',
    url: 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0728',
    pdf_name_pattern: '%Planning Systems%2021%',
    last_verified: '2025-10-14'
  },
  {
    name: 'Industry & Employment SEPP 2021',
    slug: 'sepp-industry-employment-2021',
    epi_number: '2021-0726',
    url: 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0726',
    pdf_name_pattern: '%Industry%Employment%2021%',
    last_verified: '2025-10-14'
  },
  {
    name: 'Primary Production SEPP 2021',
    slug: 'sepp-primary-production-2021',
    epi_number: '2021-0733',
    url: 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0733',
    pdf_name_pattern: '%Primary Production%2021%',
    last_verified: '2025-10-14'
  },
  {
    name: 'Sustainable Buildings SEPP 2022',
    slug: 'sepp-sustainable-buildings-2022',
    epi_number: '2022-0214',
    url: 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2022-0214',
    pdf_name_pattern: '%Sustainable Buildings%2022%',
    last_verified: '2025-10-14'
  },
  {
    name: 'Exempt & Complying Development Codes SEPP 2008',
    slug: 'sepp-exempt-complying-codes-2008',
    epi_number: '2008-0572',
    url: 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2008-0572',
    pdf_name_pattern: '%Exempt%Complying%2008%',
    last_verified: '2025-10-14'
  }
];

async function generateResearchGuide() {
  console.log('=== SEPP Amendment Research Guide ===\n');
  console.log('This guide helps you research amendments for 9 main SEPPs.\n');
  console.log('For each SEPP:');
  console.log('  1. Visit the NSW Legislation URL');
  console.log('  2. Click "Historical notes" or scroll to amendment history');
  console.log('  3. Look for EPIs gazetted after last verification date');
  console.log('  4. Record EPI number, effective date, and description\n');
  console.log('Last verification: October 14, 2025');
  console.log('Looking for amendments from: October 15, 2025 onwards\n');
  console.log('='.repeat(70));

  const researchTemplate: any[] = [];

  for (let i = 0; i < sepps.length; i++) {
    const sepp = sepps[i];
    console.log(`\n${i + 1}. ${sepp.name}`);
    console.log(`   URL: ${sepp.url}`);
    console.log(`   EPI: ${sepp.epi_number}`);
    console.log(`   Last verified: ${sepp.last_verified}`);
    console.log('   ');
    console.log('   Steps:');
    console.log('   - Visit URL above');
    console.log('   - Look for "Historical notes" section');
    console.log('   - Check for amendments since Oct 14, 2025');
    console.log('   - Record findings in sepp-amendments-research.json');

    researchTemplate.push({
      name: sepp.name,
      slug: sepp.slug,
      epi_number: sepp.epi_number,
      legislation_url: sepp.url,
      last_verified: sepp.last_verified,
      amendments_found: [],
      research_notes: '',
      research_date: new Date().toISOString().split('T')[0],
      researcher: 'PENDING'
    });
  }

  // Save template
  const fs = require('fs');
  const path = require('path');
  const outputPath = path.join(__dirname, 'sepp-amendments-research.json');

  fs.writeFileSync(outputPath, JSON.stringify({
    research_period: {
      from: '2025-10-15',
      to: new Date().toISOString().split('T')[0],
      reason: 'Updating from last verification date'
    },
    sepps: researchTemplate
  }, null, 2));

  console.log('\n' + '='.repeat(70));
  console.log(`\n✅ Research template saved to: ${outputPath}`);
  console.log('\nNext steps:');
  console.log('1. Open the JSON file');
  console.log('2. For each SEPP, visit the URL and research amendments');
  console.log('3. Fill in the amendments_found array with:');
  console.log('   {');
  console.log('     "epi": "512/2025",');
  console.log('     "effective_date": "2025-03-15",');
  console.log('     "description": "Added Part 3BA Pattern Book CDC pathway",');
  console.log('     "affects_provisions": true');
  console.log('   }');
  console.log('4. Run apply-sepp-amendments.ts to update the database\n');

  await pool.end();
}

generateResearchGuide();
