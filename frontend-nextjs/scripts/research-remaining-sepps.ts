#!/usr/bin/env tsx
/**
 * Research Remaining 8 SEPPs
 *
 * Interactive script to research amendments for the 8 SEPPs not yet researched.
 * Uses NSW Legislation Notification tab as authoritative source.
 */

import { getPool } from '@/lib/database/pool-manager';
import * as fs from 'fs';
import * as path from 'path';

const pool = getPool();

const remainingSEPPs = [
  {
    name: 'Transport & Infrastructure SEPP 2021',
    slug: 'sepp-transport-infrastructure-2021',
    epi: '2021-0732',
    url: 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0732',
    notification_search: 'Transport and Infrastructure'
  },
  {
    name: 'Biodiversity & Conservation SEPP 2021',
    slug: 'sepp-biodiversity-conservation-2021',
    epi: '2021-0722',
    url: 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0722',
    notification_search: 'Biodiversity and Conservation'
  },
  {
    name: 'Resilience & Hazards SEPP 2021',
    slug: 'sepp-resilience-hazards-2021',
    epi: '2021-0730',
    url: 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0730',
    notification_search: 'Resilience and Hazards'
  },
  {
    name: 'Planning Systems SEPP 2021',
    slug: 'sepp-planning-systems-2021',
    epi: '2021-0728',
    url: 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0728',
    notification_search: 'Planning Systems'
  },
  {
    name: 'Industry & Employment SEPP 2021',
    slug: 'sepp-industry-employment-2021',
    epi: '2021-0726',
    url: 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0726',
    notification_search: 'Industry and Employment'
  },
  {
    name: 'Primary Production SEPP 2021',
    slug: 'sepp-primary-production-2021',
    epi: '2021-0733',
    url: 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0733',
    notification_search: 'Primary Production'
  },
  {
    name: 'Sustainable Buildings SEPP 2022',
    slug: 'sepp-sustainable-buildings-2022',
    epi: '2022-0214',
    url: 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2022-0214',
    notification_search: 'Sustainable Buildings'
  },
  {
    name: 'Exempt & Complying Development Codes SEPP 2008',
    slug: 'sepp-exempt-complying-codes-2008',
    epi: '2008-0572',
    url: 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2008-0572',
    notification_search: 'Exempt and Complying Development Codes'
  }
];

async function generateResearchGuide() {
  try {
    console.log('=== SEPP Amendment Research Guide (8 Remaining SEPPs) ===\n');
    console.log('Research Period: Oct 15, 2025 → Feb 20, 2026\n');
    console.log('Source: NSW Legislation Notification Tab');
    console.log('URL: https://legislation.nsw.gov.au/browse/notifications\n');
    console.log('='.repeat(70));

    // Load existing research
    const researchPath = path.join(__dirname, 'sepp-amendments-research.json');
    const research = JSON.parse(fs.readFileSync(researchPath, 'utf8'));

    // Check database for current consolidated dates
    console.log('\n=== Current Database State ===\n');

    for (const sepp of remainingSEPPs) {
      const pattern = sepp.slug.includes('transport') ? '%Transport%Infrastructure%2021%' :
                      sepp.slug.includes('biodiversity') ? '%Biodiversity%Conservation%2021%' :
                      sepp.slug.includes('resilience') ? '%Resilience%Hazards%2021%' :
                      sepp.slug.includes('planning-systems') ? '%Planning Systems%2021%' :
                      sepp.slug.includes('industry') ? '%Industry%Employment%2021%' :
                      sepp.slug.includes('primary') ? '%Primary Production%2021%' :
                      sepp.slug.includes('sustainable') ? '%Sustainable Buildings%2022%' :
                      '%Exempt%Complying%2008%';

      const query = `
        SELECT
          id,
          consolidated_as_of_date,
          last_verified_date,
          amending_epis
        FROM documents
        WHERE document_type = 'SEPP'
          AND is_superseded = false
          AND pdf_name LIKE $1
        LIMIT 1;
      `;

      const result = await pool.query(query, [pattern]);

      if (result.rows.length > 0) {
        const doc = result.rows[0];
        console.log(`${sepp.name}:`);
        console.log(`  Consolidated: ${doc.consolidated_as_of_date?.toLocaleDateString() || 'NULL'}`);
        console.log(`  Last Verified: ${doc.last_verified_date?.toLocaleDateString() || 'NULL'}`);
        console.log(`  Current EPIs: ${doc.amending_epis || 'None'}`);
        console.log('');
      }
    }

    console.log('='.repeat(70));
    console.log('\n=== Research Instructions ===\n');

    console.log('STEP 1: Visit NSW Legislation Notification Tab');
    console.log('  URL: https://legislation.nsw.gov.au/browse/notifications');
    console.log('  Filter: Environmental Planning Instruments (EPIs)');
    console.log('  Date range: Oct 15, 2025 → Feb 20, 2026\n');

    console.log('STEP 2: For Each SEPP, Look for Amendments');
    console.log('  Search page for SEPP name (e.g., "Transport and Infrastructure")');
    console.log('  Note EPI numbers and dates (e.g., "512/2025 gazetted 31 Oct 2025")');
    console.log('  Click through to EPI to see what changed\n');

    console.log('STEP 3: Record Findings in sepp-amendments-research.json\n');

    remainingSEPPs.forEach((sepp, idx) => {
      console.log(`${idx + 1}. ${sepp.name}`);
      console.log(`   Notification search term: "${sepp.notification_search}"`);
      console.log(`   Direct URL: ${sepp.url}`);
      console.log('   Expected format in research JSON:');
      console.log('   {');
      console.log('     "epi": "XXX/202X",');
      console.log('     "effective_date": "YYYY-MM-DD",');
      console.log('     "description": "Brief summary of what changed",');
      console.log('     "affects_provisions": true|false');
      console.log('   }');
      console.log('');
    });

    console.log('='.repeat(70));
    console.log('\n=== Quick Reference: Common Amendment Types ===\n');

    console.log('✅ AFFECTS PROVISIONS (Re-extract needed):');
    console.log('  - New development pathways (CDC codes)');
    console.log('  - Changed numeric standards (lot sizes, setbacks, heights)');
    console.log('  - Modified definitions affecting rules');
    console.log('  - Removed or added clauses\n');

    console.log('ℹ️  METADATA ONLY (No re-extract):');
    console.log('  - Administrative updates (cross-references)');
    console.log('  - Commencement dates for future amendments');
    console.log('  - Corrections to maps/schedules');
    console.log('  - Procedural changes\n');

    console.log('='.repeat(70));
    console.log('\n=== After Research Complete ===\n');

    console.log('1. Save your findings to: sepp-amendments-research.json');
    console.log('2. Update researcher field from "PENDING_MANUAL" to your name');
    console.log('3. Update status from "PENDING_MANUAL_RESEARCH" to "COMPLETE"');
    console.log('4. Run: npm exec tsx scripts/apply-sepp-amendments.ts');
    console.log('5. Run: npm exec tsx scripts/standardize-amendment-references.ts');
    console.log('6. Run: npm exec tsx scripts/verify-versioning-system.ts\n');

    console.log('='.repeat(70));
    console.log('\n=== Estimated Time ===\n');
    console.log('Per SEPP: 10-15 minutes (if many amendments)');
    console.log('          5 minutes (if no amendments)');
    console.log('Total: 1-2 hours for all 8 SEPPs\n');

    console.log('TIP: Work in batches - research 2-3 SEPPs, apply to DB, verify, repeat.\n');

  } catch (error: any) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

generateResearchGuide();
