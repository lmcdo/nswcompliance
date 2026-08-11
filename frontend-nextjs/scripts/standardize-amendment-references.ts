#!/usr/bin/env tsx
/**
 * Standardize Amendment Reference Format
 *
 * Creates human-readable amendment_reference strings from amending_epis arrays
 * Format: "EPIs 512/597/647 (2025), TBD (2026)"
 */

import { getPool } from '@/lib/database/pool-manager';

const pool = getPool();

async function standardizeReferences() {
  try {
    console.log('=== Standardizing Amendment References ===\n');

    // Get all SEPPs with amending_epis
    const query = `
      SELECT
        id,
        pdf_name,
        amending_epis,
        major_amendments,
        amendment_reference
      FROM documents
      WHERE document_type = 'SEPP'
        AND is_superseded = false
        AND amending_epis IS NOT NULL
        AND array_length(amending_epis, 1) > 0;
    `;

    const result = await pool.query(query);

    console.log(`Found ${result.rows.length} SEPPs with amendment data\n`);

    let updatedCount = 0;

    for (const doc of result.rows) {
      console.log(`Processing: ${doc.pdf_name.substring(0, 60)}...`);

      // Group EPIs by year
      const episByYear: Record<string, string[]> = {};

      doc.amending_epis.forEach((epi: string) => {
        const match = epi.match(/(\d+)\/(\d{4})|TBD\/(\d{4})/);
        if (match) {
          const year = match[2] || match[3];
          const number = match[1] || 'TBD';

          if (!episByYear[year]) {
            episByYear[year] = [];
          }
          episByYear[year].push(number);
        }
      });

      // Build human-readable reference
      const referenceParts = Object.entries(episByYear)
        .sort(([yearA], [yearB]) => yearB.localeCompare(yearA)) // Most recent first
        .map(([year, numbers]) => {
          const uniqueNumbers = [...new Set(numbers)].sort((a, b) => {
            if (a === 'TBD') return 1;
            if (b === 'TBD') return -1;
            return parseInt(a) - parseInt(b);
          });
          return `${uniqueNumbers.join('/')} (${year})`;
        });

      const standardizedReference = `EPIs ${referenceParts.join(', ')}`;

      console.log(`  Current: ${doc.amendment_reference || 'NULL'}`);
      console.log(`  New: ${standardizedReference}`);

      // Update document
      const updateQuery = `
        UPDATE documents
        SET amendment_reference = $1
        WHERE id = $2;
      `;

      await pool.query(updateQuery, [standardizedReference, doc.id]);

      console.log(`  ✅ Updated`);
      console.log('');
      updatedCount++;
    }

    console.log('=== Summary ===');
    console.log(`Updated: ${updatedCount} documents`);
    console.log(`Format: "EPIs 512/597/647 (2025), TBD (2026)"`);

    // Verify all SEPPs now have consistent format
    const verifyQuery = `
      SELECT
        COUNT(*) as total,
        COUNT(amendment_reference) as with_reference,
        COUNT(amending_epis) FILTER (WHERE array_length(amending_epis, 1) > 0) as with_epis
      FROM documents
      WHERE document_type = 'SEPP'
        AND is_superseded = false;
    `;

    const stats = await pool.query(verifyQuery);
    const row = stats.rows[0];

    console.log('\n=== Verification ===');
    console.log(`Total active SEPPs: ${row.total}`);
    console.log(`With amendment_reference: ${row.with_reference}`);
    console.log(`With amending_epis data: ${row.with_epis}`);

    if (row.with_epis > 0 && row.with_reference === row.with_epis) {
      console.log('\n✅ All SEPPs with amendment data have standardized references');
    } else if (row.with_epis === 0) {
      console.log('\n✅ No amendment data yet (expected for newly initialized SEPPs)');
    } else {
      console.log(`\n⚠️  ${row.with_epis - row.with_reference} SEPPs missing standardized references`);
    }

  } catch (error: any) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

standardizeReferences();
