#!/usr/bin/env tsx
/**
 * Populate DCP Version Metadata
 *
 * Uses existing amendment_date, amendment_reference, and regulation_year
 * to populate full versioning fields for DCPs.
 */

import { getPool } from '@/lib/database/pool-manager';

const pool = getPool();

async function populateMetadata() {
  try {
    console.log('=== Populating DCP Version Metadata ===\n');

    // Step 1: Copy amendment_date to consolidated_as_of_date where available
    console.log('Step 1: Setting consolidated_as_of_date from amendment_date...');
    const consolidatedUpdate = await pool.query(`
      UPDATE documents
      SET consolidated_as_of_date = amendment_date
      WHERE document_type = 'DCP'
        AND amendment_date IS NOT NULL
        AND consolidated_as_of_date IS NULL
      RETURNING id, pdf_name, consolidated_as_of_date;
    `);

    console.log(`✅ Updated ${consolidatedUpdate.rows.length} DCPs with consolidated_as_of_date`);
    if (consolidatedUpdate.rows.length > 0) {
      consolidatedUpdate.rows.slice(0, 3).forEach(row => {
        const date = new Date(row.consolidated_as_of_date).toLocaleDateString();
        console.log(`  - ${row.pdf_name.substring(0, 60)}... → ${date}`);
      });
      if (consolidatedUpdate.rows.length > 3) {
        console.log(`  ... and ${consolidatedUpdate.rows.length - 3} more`);
      }
    }
    console.log('');

    // Step 2: For DCPs without amendment_date, use last_verified_date
    console.log('Step 2: Using last_verified_date as fallback...');
    const fallbackUpdate = await pool.query(`
      UPDATE documents
      SET consolidated_as_of_date = last_verified_date
      WHERE document_type = 'DCP'
        AND last_verified_date IS NOT NULL
        AND consolidated_as_of_date IS NULL
      RETURNING id, pdf_name, consolidated_as_of_date;
    `);

    console.log(`✅ Updated ${fallbackUpdate.rows.length} DCPs with fallback consolidated_as_of_date`);
    console.log('');

    // Step 3: Set next_check_date = consolidated_as_of_date + 60 days (DCPs change more frequently)
    console.log('Step 3: Setting next check dates (60 days for DCPs)...');
    const checkDateUpdate = await pool.query(`
      UPDATE documents
      SET next_check_date = consolidated_as_of_date + INTERVAL '60 days'
      WHERE document_type = 'DCP'
        AND consolidated_as_of_date IS NOT NULL
        AND next_check_date IS NULL
      RETURNING id, pdf_name, consolidated_as_of_date, next_check_date;
    `);

    console.log(`✅ Updated ${checkDateUpdate.rows.length} DCPs with next_check_date`);
    if (checkDateUpdate.rows.length > 0) {
      checkDateUpdate.rows.slice(0, 3).forEach(row => {
        const consolidated = new Date(row.consolidated_as_of_date).toLocaleDateString();
        const nextCheck = new Date(row.next_check_date).toLocaleDateString();
        console.log(`  - ${row.pdf_name.substring(0, 50)}...`);
        console.log(`    Consolidated: ${consolidated} → Next check: ${nextCheck}`);
      });
      if (checkDateUpdate.rows.length > 3) {
        console.log(`  ... and ${checkDateUpdate.rows.length - 3} more`);
      }
    }
    console.log('');

    // Step 4: Standardize amendment_reference format
    console.log('Step 4: Standardizing amendment_reference format...');

    // Pattern: "IWLEP 2022" → "IWLEP 2022 amendments"
    // Pattern: "Amendment 23" → keep as-is
    // Pattern: NULL → "No amendments recorded"

    const refUpdate = await pool.query(`
      UPDATE documents
      SET amendment_reference = CASE
        WHEN amendment_reference LIKE 'IWLEP%' AND amendment_reference NOT LIKE '%amendments%'
          THEN amendment_reference || ' amendments'
        WHEN amendment_reference IS NULL AND regulation_year IS NOT NULL
          THEN 'Base version ' || regulation_year::text
        ELSE amendment_reference
      END
      WHERE document_type = 'DCP'
      RETURNING id, pdf_name, amendment_reference;
    `);

    console.log(`✅ Standardized ${refUpdate.rows.length} amendment references`);
    console.log('');

    // Step 5: Set version_status = 'current' for DCPs with recent verification
    console.log('Step 5: Setting version_status to "current"...');
    const statusUpdate = await pool.query(`
      UPDATE documents
      SET version_status = 'current'
      WHERE document_type = 'DCP'
        AND last_verified_date >= CURRENT_DATE - INTERVAL '180 days'
        AND (version_status IS NULL OR version_status = 'unverified')
      RETURNING id, pdf_name, version_status, last_verified_date;
    `);

    console.log(`✅ Updated ${statusUpdate.rows.length} DCPs to version_status='current'`);
    console.log('');

    // Final summary
    console.log('=== Final Summary ===');
    const summary = await pool.query(`
      SELECT
        COUNT(*) FILTER (WHERE regulation_year IS NOT NULL) as has_year,
        COUNT(*) FILTER (WHERE consolidated_as_of_date IS NOT NULL) as has_consolidated_date,
        COUNT(*) FILTER (WHERE next_check_date IS NOT NULL) as has_next_check,
        COUNT(*) FILTER (WHERE amendment_reference IS NOT NULL) as has_ref,
        COUNT(*) FILTER (WHERE version_status = 'current') as status_current,
        COUNT(*) as total_documents
      FROM documents
      WHERE document_type = 'DCP';
    `);

    const stats = summary.rows[0];
    console.log(`Total DCP documents: ${stats.total_documents}`);
    console.log('');
    console.log('Metadata population:');
    console.log(`  regulation_year:           ${stats.has_year}/${stats.total_documents}`);
    console.log(`  consolidated_as_of_date:   ${stats.has_consolidated_date}/${stats.total_documents}`);
    console.log(`  next_check_date:           ${stats.has_next_check}/${stats.total_documents}`);
    console.log(`  amendment_reference:       ${stats.has_ref}/${stats.total_documents}`);
    console.log(`  version_status='current':  ${stats.status_current}/${stats.total_documents}`);

    // Check for overdue reviews
    const overdueQuery = `
      SELECT COUNT(*) as count
      FROM documents
      WHERE document_type = 'DCP'
        AND next_check_date IS NOT NULL
        AND next_check_date < CURRENT_DATE;
    `;

    const overdueResult = await pool.query(overdueQuery);
    const overdueCount = parseInt(overdueResult.rows[0].count);

    if (overdueCount > 0) {
      console.log('');
      console.log(`⚠️  ${overdueCount} DCPs are overdue for review`);
      console.log('   Run: SELECT * FROM documents WHERE document_type=\'DCP\' AND next_check_date < CURRENT_DATE;');
    } else {
      console.log('');
      console.log('✅ All DCPs have future review dates (none overdue)');
    }

  } catch (error: any) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

populateMetadata();
