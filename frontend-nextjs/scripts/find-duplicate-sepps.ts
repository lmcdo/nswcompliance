#!/usr/bin/env tsx
import { getPool } from '@/lib/database/pool-manager';

const pool = getPool();

async function findDuplicates() {
  try {
    console.log('=== Finding Duplicate SEPP Documents ===\n');

    // Find documents with duplicate pdf_name
    const duplicatesQuery = `
      SELECT
        pdf_name,
        COUNT(*) as duplicate_count,
        ARRAY_AGG(id ORDER BY last_verified_date DESC NULLS LAST, id) as document_ids,
        ARRAY_AGG(last_verified_date ORDER BY last_verified_date DESC NULLS LAST, id) as verified_dates,
        ARRAY_AGG(version_status ORDER BY last_verified_date DESC NULLS LAST, id) as statuses,
        MAX(last_verified_date) as most_recent_verification
      FROM documents
      WHERE document_type = 'SEPP'
        AND pdf_name IS NOT NULL
      GROUP BY pdf_name
      HAVING COUNT(*) > 1
      ORDER BY COUNT(*) DESC, pdf_name;
    `;

    const result = await pool.query(duplicatesQuery);

    if (result.rows.length === 0) {
      console.log('✅ No duplicate SEPP documents found!');
      await pool.end();
      return;
    }

    console.log(`Found ${result.rows.length} SEPP documents with duplicates:\n`);

    let totalDuplicates = 0;
    const supersedeCandidates: Array<{
      pdf_name: string;
      keep_id: string;
      supersede_ids: string[];
    }> = [];

    result.rows.forEach((row, index) => {
      const duplicateCount = row.duplicate_count - 1; // Subtract the one we'll keep
      totalDuplicates += duplicateCount;

      console.log(`${index + 1}. ${row.pdf_name}`);
      console.log(`   Duplicates: ${row.duplicate_count} copies`);
      console.log(`   Document IDs:`);

      row.document_ids.forEach((id: string, idx: number) => {
        const verifiedDate = row.verified_dates[idx]
          ? new Date(row.verified_dates[idx]).toLocaleDateString()
          : 'Never verified';
        const status = row.statuses[idx] || 'NULL';
        const marker = idx === 0 ? '✓ KEEP' : '✗ SUPERSEDE';

        console.log(`     ${marker}: ${id}`);
        console.log(`            Verified: ${verifiedDate}, Status: ${status}`);
      });
      console.log('');

      // Strategy: Keep the first one (most recently verified), mark rest as superseded
      supersedeCandidates.push({
        pdf_name: row.pdf_name,
        keep_id: row.document_ids[0],
        supersede_ids: row.document_ids.slice(1)
      });
    });

    console.log('=== Summary ===');
    console.log(`Total SEPP documents with duplicates: ${result.rows.length}`);
    console.log(`Total documents to mark as superseded: ${totalDuplicates}`);
    console.log('');

    // Get provision counts for documents being superseded
    const provisionCheckQuery = `
      SELECT
        d.id,
        d.pdf_name,
        COUNT(rp.id) as provision_count,
        COUNT(rp.id) FILTER (WHERE rp.is_current) as current_provision_count
      FROM documents d
      LEFT JOIN regulatory_provisions rp ON rp.document_id = d.id
      WHERE d.id = ANY($1)
      GROUP BY d.id, d.pdf_name
      HAVING COUNT(rp.id) > 0
      ORDER BY COUNT(rp.id) DESC;
    `;

    const allSupersededIds = supersedeCandidates.flatMap(c => c.supersede_ids);
    const provisionCheck = await pool.query(provisionCheckQuery, [allSupersededIds]);

    if (provisionCheck.rows.length > 0) {
      console.log('⚠️  WARNING: Some documents being superseded have provisions:');
      console.log('');
      provisionCheck.rows.forEach(row => {
        console.log(`  ${row.id}`);
        console.log(`    ${row.provision_count} provisions`);
      });
      console.log('');
      console.log('RECOMMENDATION: Verify provisions are duplicated in the kept document');
      console.log('                before marking as superseded.');
    } else {
      console.log('✅ All documents being superseded have 0 provisions (safe to supersede)');
    }

    console.log('');

    // Save cleanup plan to JSON
    const cleanupPlan = {
      generated_at: new Date().toISOString(),
      total_duplicates: result.rows.length,
      total_to_supersede: totalDuplicates,
      actions: supersedeCandidates.map(c => ({
        pdf_name: c.pdf_name,
        action: 'keep',
        document_id: c.keep_id,
        supersede: c.supersede_ids.map(id => ({
          document_id: id,
          action: 'mark_superseded'
        }))
      }))
    };

    const fs = require('fs');
    const path = require('path');
    const outputPath = path.join(__dirname, 'sepp-duplicate-cleanup-plan.json');
    fs.writeFileSync(outputPath, JSON.stringify(cleanupPlan, null, 2));

    console.log(`📄 Cleanup plan saved to: ${outputPath}`);
    console.log('');
    console.log('Next step: Review the plan, then run cleanup-duplicate-sepps.ts');

  } catch (error: any) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

findDuplicates();
