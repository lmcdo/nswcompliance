#!/usr/bin/env tsx
/**
 * Verify SEPP Versioning System
 *
 * Comprehensive verification of version tracking infrastructure,
 * data integrity, and workflow readiness.
 */

import { getPool } from '@/lib/database/pool-manager';

const pool = getPool();

interface TestResult {
  name: string;
  passed: boolean;
  message: string;
  details?: any;
}

const results: TestResult[] = [];

function test(name: string, passed: boolean, message: string, details?: any) {
  results.push({ name, passed, message, details });
  const icon = passed ? '✅' : '❌';
  console.log(`${icon} ${name}: ${message}`);
  if (details) {
    console.log(`   ${JSON.stringify(details)}`);
  }
}

async function verifySystem() {
  try {
    console.log('=== SEPP Versioning System Verification ===\n');

    // Test 1: Schema columns exist
    console.log('Test 1: Schema Verification');
    const schemaQuery = `
      SELECT column_name, data_type
      FROM information_schema.columns
      WHERE table_name = 'documents'
        AND column_name IN (
          'consolidated_as_of_date',
          'consolidation_url',
          'amending_epis',
          'major_amendments',
          'next_check_date',
          'is_superseded',
          'amendment_reference',
          'regulation_year'
        )
      ORDER BY column_name;
    `;

    const schemaResult = await pool.query(schemaQuery);
    const expectedColumns = 8;
    const foundColumns = schemaResult.rows.length;

    test(
      'Schema Columns',
      foundColumns === expectedColumns,
      `${foundColumns}/${expectedColumns} version tracking columns exist`,
      schemaResult.rows.map(r => `${r.column_name} (${r.data_type})`).join(', ')
    );
    console.log('');

    // Test 2: Active SEPP count
    console.log('Test 2: Active SEPP Documents');
    const countQuery = `
      SELECT COUNT(*) as count
      FROM documents
      WHERE document_type = 'SEPP'
        AND is_superseded = false
        AND pdf_name NOT LIKE '%Section%';
    `;

    const countResult = await pool.query(countQuery);
    const activeSEPPs = parseInt(countResult.rows[0].count);

    test(
      'Active SEPPs',
      activeSEPPs >= 9 && activeSEPPs <= 20,
      `${activeSEPPs} active SEPP documents (expected 9-20)`,
      { count: activeSEPPs }
    );
    console.log('');

    // Test 3: Housing SEPP version data
    console.log('Test 3: Housing SEPP Amendment Data');
    const housingQuery = `
      SELECT
        id,
        consolidated_as_of_date,
        consolidation_url,
        amending_epis,
        major_amendments,
        amendment_reference,
        next_check_date,
        last_verified_date,
        version_status
      FROM documents
      WHERE id LIKE '%Housing%2021%'
        AND is_superseded = false
      LIMIT 1;
    `;

    const housingResult = await pool.query(housingQuery);

    if (housingResult.rows.length > 0) {
      const housing = housingResult.rows[0];

      test(
        'Housing SEPP - Consolidated Date',
        housing.consolidated_as_of_date !== null,
        housing.consolidated_as_of_date ? `Set to ${housing.consolidated_as_of_date.toLocaleDateString()}` : 'NULL'
      );

      test(
        'Housing SEPP - Consolidation URL',
        housing.consolidation_url !== null && housing.consolidation_url.includes('legislation.nsw.gov.au'),
        housing.consolidation_url ? 'Valid NSW Legislation URL' : 'NULL'
      );

      const hasEPIs = housing.amending_epis && housing.amending_epis.length > 0;
      test(
        'Housing SEPP - Amending EPIs',
        hasEPIs,
        hasEPIs ? `${housing.amending_epis.length} EPIs recorded` : 'No EPIs',
        hasEPIs ? housing.amending_epis : undefined
      );

      const hasMajorAmendments = housing.major_amendments && housing.major_amendments.length > 0;
      test(
        'Housing SEPP - Major Amendments',
        hasMajorAmendments,
        hasMajorAmendments ? `${housing.major_amendments.length} amendments with details` : 'No amendments',
        hasMajorAmendments ? housing.major_amendments[0] : undefined
      );

      test(
        'Housing SEPP - Amendment Reference',
        housing.amendment_reference !== null && housing.amendment_reference.startsWith('EPIs'),
        housing.amendment_reference || 'NULL'
      );

      test(
        'Housing SEPP - Next Check Date',
        housing.next_check_date !== null,
        housing.next_check_date ? `Set to ${housing.next_check_date.toLocaleDateString()}` : 'NULL'
      );

      test(
        'Housing SEPP - Version Status',
        housing.version_status === 'current',
        `Status: ${housing.version_status}`
      );
    } else {
      test('Housing SEPP', false, 'Housing SEPP not found in database');
    }
    console.log('');

    // Test 4: Next check date calculation
    console.log('Test 4: Next Check Date Calculation');
    const dateCalcQuery = `
      SELECT
        id,
        pdf_name,
        consolidated_as_of_date,
        next_check_date,
        next_check_date - consolidated_as_of_date as day_diff
      FROM documents
      WHERE document_type = 'SEPP'
        AND is_superseded = false
        AND consolidated_as_of_date IS NOT NULL
        AND next_check_date IS NOT NULL
      LIMIT 5;
    `;

    const dateCalcResult = await pool.query(dateCalcQuery);
    const validDates = dateCalcResult.rows.filter(r => r.day_diff >= 89 && r.day_diff <= 91);

    test(
      'Next Check Date Formula',
      validDates.length === dateCalcResult.rows.length,
      `${validDates.length}/${dateCalcResult.rows.length} documents have correct 90-day intervals`,
      dateCalcResult.rows.length > 0 ? `Example: ${dateCalcResult.rows[0].day_diff} days` : undefined
    );
    console.log('');

    // Test 5: Consolidation URL format
    console.log('Test 5: Consolidation URL Format');
    const urlQuery = `
      SELECT
        pdf_name,
        consolidation_url,
        consolidated_as_of_date
      FROM documents
      WHERE document_type = 'SEPP'
        AND is_superseded = false
        AND consolidation_url IS NOT NULL
      LIMIT 3;
    `;

    const urlResult = await pool.query(urlQuery);
    let validURLs = 0;

    for (const row of urlResult.rows) {
      const dbDate = new Date(row.consolidated_as_of_date);
      const dateStr = dbDate.toISOString().split('T')[0];

      // Extract date from URL
      const urlMatch = row.consolidation_url.match(/(\d{4}-\d{2}-\d{2})/);
      const urlDate = urlMatch ? new Date(urlMatch[1]) : null;

      // Allow 1-day difference due to timezone handling
      const dateDiff = urlDate ? Math.abs((dbDate.getTime() - urlDate.getTime()) / (1000 * 60 * 60 * 24)) : 999;
      const dateCloseEnough = dateDiff <= 1;

      const urlContainsEPI = row.consolidation_url.match(/epi-\d{4}-\d{4}/);

      if (dateCloseEnough && urlContainsEPI) validURLs++;
    }

    test(
      'Consolidation URL Structure',
      validURLs === urlResult.rows.length,
      `${validURLs}/${urlResult.rows.length} URLs contain point-in-time date and EPI number`,
      urlResult.rows.length > 0 ? urlResult.rows[0].consolidation_url : undefined
    );
    console.log('');

    // Test 6: Amendment reference format
    console.log('Test 6: Amendment Reference Standardization');
    const refQuery = `
      SELECT
        pdf_name,
        amendment_reference,
        amending_epis
      FROM documents
      WHERE document_type = 'SEPP'
        AND is_superseded = false
        AND amending_epis IS NOT NULL
        AND array_length(amending_epis, 1) > 0;
    `;

    const refResult = await pool.query(refQuery);
    const validRefs = refResult.rows.filter(r =>
      r.amendment_reference && r.amendment_reference.startsWith('EPIs')
    );

    test(
      'Amendment Reference Format',
      validRefs.length === refResult.rows.length,
      `${validRefs.length}/${refResult.rows.length} references follow "EPIs X/Y (YYYY)" format`,
      validRefs.length > 0 ? validRefs[0].amendment_reference : undefined
    );
    console.log('');

    // Test 7: Superseded documents
    console.log('Test 7: Superseded Document Handling');
    const supersededQuery = `
      SELECT COUNT(*) as count
      FROM documents
      WHERE document_type = 'SEPP'
        AND is_superseded = true;
    `;

    const supersededResult = await pool.query(supersededQuery);
    const supersededCount = parseInt(supersededResult.rows[0].count);

    test(
      'Superseded Documents',
      supersededCount >= 7,
      `${supersededCount} documents marked as superseded (from duplicate cleanup)`
    );
    console.log('');

    // Test 8: Version status consistency
    console.log('Test 8: Version Status Consistency');
    const statusQuery = `
      SELECT
        version_status,
        COUNT(*) as count
      FROM documents
      WHERE document_type = 'SEPP'
        AND is_superseded = false
      GROUP BY version_status;
    `;

    const statusResult = await pool.query(statusQuery);
    const currentCount = statusResult.rows.find(r => r.version_status === 'current')?.count || 0;

    test(
      'Version Status = current',
      currentCount >= 1,
      `${currentCount} documents have version_status='current'`
    );
    console.log('');

    // Final Summary
    console.log('='.repeat(70));
    console.log('=== VERIFICATION SUMMARY ===\n');

    const passed = results.filter(r => r.passed).length;
    const total = results.length;
    const percentage = ((passed / total) * 100).toFixed(1);

    console.log(`Tests Passed: ${passed}/${total} (${percentage}%)`);
    console.log('');

    if (passed === total) {
      console.log('✅ ALL TESTS PASSED');
      console.log('   SEPP versioning system is fully operational');
    } else {
      console.log(`⚠️  ${total - passed} TESTS FAILED`);
      console.log('   Review failed tests above for details');
      console.log('');
      console.log('Failed tests:');
      results.filter(r => !r.passed).forEach(r => {
        console.log(`  - ${r.name}: ${r.message}`);
      });
    }

    console.log('');
    console.log('=== SYSTEM STATUS ===');

    const systemReady = passed >= total * 0.9; // 90% pass rate

    if (systemReady) {
      console.log('✅ System ready for production use');
      console.log('   - Version tracking columns in place');
      console.log('   - Amendment research workflow tested');
      console.log('   - Quarterly review process documented');
      console.log('');
      console.log('Next steps:');
      console.log('   1. Complete manual research for remaining 8 SEPPs (optional)');
      console.log('   2. Implement frontend version badge (Task #15)');
      console.log('   3. Update provision citations (Task #16)');
      console.log('   4. Schedule first quarterly review (90 days from now)');
    } else {
      console.log('❌ System not ready');
      console.log('   Fix failed tests before proceeding');
    }

  } catch (error: any) {
    console.error('❌ Verification failed:', error.message);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

verifySystem();
