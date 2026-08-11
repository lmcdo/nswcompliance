#!/usr/bin/env tsx
/**
 * Fix Versioning Date Issues
 *
 * Corrects:
 * 1. Next check dates to be exactly 90 days from consolidated_as_of_date
 * 2. Consolidation URLs to use current consolidated_as_of_date (not old last_verified_date)
 */

import { getPool } from '@/lib/database/pool-manager';

const pool = getPool();

async function fixDates() {
  try {
    console.log('=== Fixing Versioning Date Issues ===\n');

    // Fix 1: Recalculate next_check_date = consolidated_as_of_date + 90 days
    console.log('Fix 1: Recalculating next check dates...');

    const fixCheckDateQuery = `
      UPDATE documents
      SET next_check_date = consolidated_as_of_date + INTERVAL '90 days'
      WHERE document_type = 'SEPP'
        AND is_superseded = false
        AND consolidated_as_of_date IS NOT NULL
      RETURNING id, pdf_name, consolidated_as_of_date, next_check_date;
    `;

    const checkDateResult = await pool.query(fixCheckDateQuery);

    console.log(`✅ Updated ${checkDateResult.rows.length} documents`);
    checkDateResult.rows.slice(0, 3).forEach(row => {
      const consolidated = new Date(row.consolidated_as_of_date).toLocaleDateString();
      const nextCheck = new Date(row.next_check_date).toLocaleDateString();
      console.log(`  - ${row.pdf_name.substring(0, 50)}...`);
      console.log(`    Consolidated: ${consolidated} → Next: ${nextCheck}`);
    });
    console.log('');

    // Fix 2: Regenerate consolidation URLs using current consolidated_as_of_date
    console.log('Fix 2: Regenerating consolidation URLs...');

    const fixURLQuery = `
      UPDATE documents
      SET consolidation_url = CASE
        -- Housing SEPP 2021
        WHEN pdf_name LIKE '%Housing%2021%' THEN
          'https://legislation.nsw.gov.au/view/whole/html/' ||
          TO_CHAR(consolidated_as_of_date, 'YYYY-MM-DD') ||
          '/epi-2021-0714'

        -- Transport & Infrastructure SEPP 2021
        WHEN pdf_name LIKE '%Transport%Infrastructure%2021%' THEN
          'https://legislation.nsw.gov.au/view/whole/html/' ||
          TO_CHAR(consolidated_as_of_date, 'YYYY-MM-DD') ||
          '/epi-2021-0732'

        -- Biodiversity & Conservation SEPP 2021
        WHEN pdf_name LIKE '%Biodiversity%Conservation%2021%' THEN
          'https://legislation.nsw.gov.au/view/whole/html/' ||
          TO_CHAR(consolidated_as_of_date, 'YYYY-MM-DD') ||
          '/epi-2021-0722'

        -- Resilience & Hazards SEPP 2021
        WHEN pdf_name LIKE '%Resilience%Hazards%2021%' THEN
          'https://legislation.nsw.gov.au/view/whole/html/' ||
          TO_CHAR(consolidated_as_of_date, 'YYYY-MM-DD') ||
          '/epi-2021-0730'

        -- Planning Systems SEPP 2021
        WHEN pdf_name LIKE '%Planning Systems%2021%' THEN
          'https://legislation.nsw.gov.au/view/whole/html/' ||
          TO_CHAR(consolidated_as_of_date, 'YYYY-MM-DD') ||
          '/epi-2021-0728'

        -- Industry & Employment SEPP 2021
        WHEN pdf_name LIKE '%Industry%Employment%2021%' THEN
          'https://legislation.nsw.gov.au/view/whole/html/' ||
          TO_CHAR(consolidated_as_of_date, 'YYYY-MM-DD') ||
          '/epi-2021-0726'

        -- Primary Production SEPP 2021
        WHEN pdf_name LIKE '%Primary Production%2021%' THEN
          'https://legislation.nsw.gov.au/view/whole/html/' ||
          TO_CHAR(consolidated_as_of_date, 'YYYY-MM-DD') ||
          '/epi-2021-0733'

        -- Sustainable Buildings SEPP 2022
        WHEN pdf_name LIKE '%Sustainable Buildings%2022%' THEN
          'https://legislation.nsw.gov.au/view/whole/html/' ||
          TO_CHAR(consolidated_as_of_date, 'YYYY-MM-DD') ||
          '/epi-2022-0214'

        -- Exempt & Complying Codes SEPP 2008
        WHEN pdf_name LIKE '%Exempt%Complying%2008%' THEN
          'https://legislation.nsw.gov.au/view/whole/html/' ||
          TO_CHAR(consolidated_as_of_date, 'YYYY-MM-DD') ||
          '/epi-2008-0572'

        ELSE consolidation_url
      END
      WHERE document_type = 'SEPP'
        AND is_superseded = false
        AND consolidated_as_of_date IS NOT NULL
      RETURNING id, pdf_name, consolidation_url;
    `;

    const urlResult = await pool.query(fixURLQuery);

    console.log(`✅ Updated ${urlResult.rows.length} consolidation URLs`);
    urlResult.rows.slice(0, 2).forEach(row => {
      console.log(`  - ${row.pdf_name.substring(0, 40)}...`);
      console.log(`    ${row.consolidation_url}`);
    });
    console.log('');

    // Verify fixes
    console.log('=== Verification ===');

    const verifyQuery = `
      SELECT
        pdf_name,
        consolidated_as_of_date,
        next_check_date,
        next_check_date - consolidated_as_of_date as day_diff,
        consolidation_url
      FROM documents
      WHERE document_type = 'SEPP'
        AND is_superseded = false
        AND consolidated_as_of_date IS NOT NULL
      ORDER BY pdf_name
      LIMIT 5;
    `;

    const verifyResult = await pool.query(verifyQuery);

    verifyResult.rows.forEach(row => {
      const dateMatch = row.consolidation_url?.match(/(\d{4}-\d{2}-\d{2})/);
      const urlDate = dateMatch ? dateMatch[1] : 'NO_DATE';
      const expectedDate = new Date(row.consolidated_as_of_date).toISOString().split('T')[0];
      const urlCorrect = urlDate === expectedDate;
      const dayDiffCorrect = row.day_diff >= 89 && row.day_diff <= 91; // Allow 89-91 for month length variations

      console.log(`${row.pdf_name.substring(0, 50)}...`);
      console.log(`  Day diff: ${row.day_diff} ${dayDiffCorrect ? '✅' : '❌'}`);
      console.log(`  URL date: ${urlDate} ${urlCorrect ? '✅' : '❌'}`);
      console.log('');
    });

    console.log('✅ Date fixes applied successfully');

  } catch (error: any) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

fixDates();
