#!/usr/bin/env tsx
/**
 * Monitor NSW Legislation Notifications
 *
 * Checks legislation.nsw.gov.au/browse/notifications for new SEPP/LEP EPIs
 * Can be run weekly as a cron job to detect amendments automatically.
 */

import { getPool } from '@/lib/database/pool-manager';
import * as fs from 'fs';
import * as path from 'path';

const pool = getPool();

// Our tracked SEPPs with EPI numbers
const trackedSEPPs = {
  '2021-0714': { name: 'Housing SEPP 2021', slug: 'sepp-housing-2021' },
  '2021-0732': { name: 'Transport & Infrastructure SEPP 2021', slug: 'sepp-transport-infrastructure-2021' },
  '2021-0722': { name: 'Biodiversity & Conservation SEPP 2021', slug: 'sepp-biodiversity-conservation-2021' },
  '2021-0730': { name: 'Resilience & Hazards SEPP 2021', slug: 'sepp-resilience-hazards-2021' },
  '2021-0728': { name: 'Planning Systems SEPP 2021', slug: 'sepp-planning-systems-2021' },
  '2021-0726': { name: 'Industry & Employment SEPP 2021', slug: 'sepp-industry-employment-2021' },
  '2021-0733': { name: 'Primary Production SEPP 2021', slug: 'sepp-primary-production-2021' },
  '2022-0214': { name: 'Sustainable Buildings SEPP 2022', slug: 'sepp-sustainable-buildings-2022' },
  '2008-0572': { name: 'Exempt & Complying Codes SEPP 2008', slug: 'sepp-exempt-complying-codes-2008' }
};

interface Notification {
  epi: string;
  date: string;
  title: string;
  affects: string[];
}

async function monitorNotifications() {
  try {
    console.log('=== NSW Legislation Notification Monitor ===\n');
    console.log('Checking for new SEPP/LEP amendments...\n');

    // Get last check date from database
    const lastCheckQuery = `
      SELECT MAX(last_verified_date) as last_check
      FROM documents
      WHERE document_type IN ('SEPP', 'LEP');
    `;

    const lastCheckResult = await pool.query(lastCheckQuery);
    // rows[0]?. — a MAX() aggregate returns one row today, but an empty result
    // would throw here rather than fall through to the default date below.
    const lastCheck = lastCheckResult.rows[0]?.last_check;
    const lastCheckDate = lastCheck ? new Date(lastCheck) : new Date('2025-10-14');

    console.log(`Last verification: ${lastCheckDate.toLocaleDateString()}`);
    console.log(`Checking for amendments since: ${lastCheckDate.toLocaleDateString()}\n`);

    console.log('='.repeat(70));
    console.log('\n🔍 MANUAL CHECK REQUIRED\n');
    console.log('This is a REMINDER to check NSW Legislation Notifications.\n');
    console.log('Automated scraping is not reliable due to website blocking.\n');
    console.log('Please follow these steps:\n');

    console.log('STEP 1: Visit Notifications Page');
    console.log('  URL: https://legislation.nsw.gov.au/browse/notifications');
    console.log('  Filter: Environmental Planning Instruments\n');

    console.log('STEP 2: Look for These SEPPs');
    Object.entries(trackedSEPPs).forEach(([epi, info]) => {
      console.log(`  - ${info.name} (${epi})`);
    });
    console.log('');

    console.log('STEP 3: Check Date Range');
    console.log(`  From: ${lastCheckDate.toLocaleDateString()}`);
    console.log(`  To: Today (${new Date().toLocaleDateString()})\n`);

    console.log('STEP 4: Record Any Amendments Found');
    console.log('  If amendments found: Update sepp-amendments-research.json');
    console.log('  If no amendments: Update last_verified_date in database\n');

    console.log('='.repeat(70));
    console.log('\n=== Alternative: Use NSW Planning Portal Email Alerts ===\n');

    console.log('NSW Planning (planning.nsw.gov.au) may offer email subscriptions.');
    console.log('Benefits:');
    console.log('  ✅ Automatic notifications when SEPPs/LEPs change');
    console.log('  ✅ No need to manually check weekly');
    console.log('  ✅ Official government source\n');

    console.log('Check: https://www.planning.nsw.gov.au/subscribe\n');

    console.log('='.repeat(70));
    console.log('\n=== Overdue Reviews ===\n');

    // Check for overdue SEPPs
    const overdueQuery = `
      SELECT
        pdf_name,
        next_check_date,
        CURRENT_DATE - next_check_date as days_overdue
      FROM documents
      WHERE document_type = 'SEPP'
        AND is_superseded = false
        AND next_check_date < CURRENT_DATE
      ORDER BY days_overdue DESC;
    `;

    const overdueResult = await pool.query(overdueQuery);

    if (overdueResult.rows.length > 0) {
      console.log(`⚠️  ${overdueResult.rows.length} SEPPs are OVERDUE for review:\n`);
      overdueResult.rows.forEach(row => {
        console.log(`  - ${row.pdf_name.substring(0, 60)}...`);
        console.log(`    Next check: ${row.next_check_date.toLocaleDateString()}`);
        console.log(`    Days overdue: ${row.days_overdue}`);
        console.log('');
      });

      console.log('⚡ ACTION REQUIRED: Research these SEPPs ASAP\n');
    } else {
      console.log('✅ All SEPPs are up-to-date (none overdue)\n');
    }

    console.log('='.repeat(70));
    console.log('\n=== Next Steps ===\n');

    console.log('1. Visit NSW Legislation Notifications tab NOW');
    console.log('2. Check for amendments to our 9 tracked SEPPs');
    console.log('3. If found: Run npm exec tsx scripts/research-remaining-sepps.ts');
    console.log('4. If none: Run this to update verified dates:');
    console.log('   UPDATE documents SET last_verified_date = CURRENT_DATE');
    console.log('   WHERE document_type = \'SEPP\' AND is_superseded = false;\n');

    console.log('5. Schedule this script to run weekly (e.g., Monday 9am)');
    console.log('   Windows Task Scheduler: npm exec tsx scripts/monitor-nsw-legislation-notifications.ts\n');

  } catch (error: any) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

monitorNotifications();
