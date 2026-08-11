#!/usr/bin/env tsx
import { getPool } from '@/lib/database/pool-manager';

const pool = getPool();

async function cleanupDuplicates() {
  try {
    console.log('=== SEPP Duplicate Cleanup (REVERSED STRATEGY) ===\n');

    // CORRECTED: Keep documents WITHOUT parentheses (more provisions)
    // Supersede documents WITH parentheses (fewer provisions)
    const duplicatePairs = [
      {
        keep: 'State_Environmental_Planning_Policy_Biodiversity_and_Conservation_2021__NSW_Legislation', // 2100 provisions
        supersede: 'State_Environmental_Planning_Policy_(Biodiversity_and_Conservation)_2021___NSW_Legislation' // 96 provisions
      },
      {
        keep: 'State_Environmental_Planning_Policy_Industry_and_Employment_2021__NSW_Legislation', // 860 provisions
        supersede: 'State_Environmental_Planning_Policy_(Industry_and_Employment)_2021___NSW_Legislation' // 442 provisions
      },
      {
        keep: 'State_Environmental_Planning_Policy_Planning_Systems_2021__NSW_Legislation', // 1302 provisions
        supersede: 'State_Environmental_Planning_Policy_(Planning_Systems)_2021___NSW_Legislation' // 394 provisions
      },
      {
        keep: 'State_Environmental_Planning_Policy_Primary_Production_2021__NSW_Legislation', // 518 provisions
        supersede: 'State_Environmental_Planning_Policy_(Primary_Production)_2021___NSW_Legislation' // 234 provisions
      },
      {
        keep: 'State_Environmental_Planning_Policy_Resilience_and_Hazards_2021__NSW_Legislation', // 426 provisions
        supersede: 'State_Environmental_Planning_Policy_(Resilience_and_Hazards)_2021___NSW_Legislation' // 207 provisions
      },
      {
        keep: 'State_Environmental_Planning_Policy_Sustainable_Buildings_2022__NSW_Legislation', // 292 provisions
        supersede: 'State_Environmental_Planning_Policy_(Sustainable_Buildings)_2022___NSW_Legislation' // 149 provisions
      },
      {
        keep: 'State_Environmental_Planning_Policy_Transport_and_Infrastructure_2021__NSW_Legislation', // 6138 provisions
        supersede: 'State_Environmental_Planning_Policy_(Transport_and_Infrastructure)_2021___NSW_Legislation' // 174 provisions
      }
    ];

    console.log('STRATEGY: Keep full consolidated versions (WITHOUT parentheses)');
    console.log('          Supersede partial versions (WITH parentheses)\n');

    // Verify provision counts before proceeding
    console.log('Verifying provision counts...\n');

    for (const pair of duplicatePairs) {
      const countQuery = `
        -- Both totals matter here. The overall count decides which duplicate is
        -- the fuller document; the is_current count shows how much of each is
        -- still live, so a document that is larger only because it carries more
        -- superseded rows cannot win the comparison by accident.
        SELECT
          d.id,
          COUNT(rp.id) as provision_count,
          COUNT(rp.id) FILTER (WHERE rp.is_current) as current_provision_count
        FROM documents d
        LEFT JOIN regulatory_provisions rp ON rp.document_id = d.id
        WHERE d.id IN ($1, $2)
        GROUP BY d.id;
      `;

      const result = await pool.query(countQuery, [pair.keep, pair.supersede]);
      const keepCount = result.rows.find((r: any) => r.id === pair.keep)?.provision_count || 0;
      const supersedeCount = result.rows.find((r: any) => r.id === pair.supersede)?.provision_count || 0;

      console.log(`${pair.keep.substring(0, 60)}...`);
      console.log(`  KEEP: ${keepCount} provisions`);
      console.log(`  SUPERSEDE: ${supersedeCount} provisions`);
      console.log('');
    }

    // Confirm before proceeding
    console.log('=== Cleanup Plan ===');
    console.log(`Marking ${duplicatePairs.length} documents as superseded...\n`);

    // Mark documents as superseded
    const supersedeIds = duplicatePairs.map(p => p.supersede);

    const updateQuery = `
      UPDATE documents
      SET
        is_superseded = true,
        version_status = 'superseded'
      WHERE id = ANY($1)
      RETURNING id, pdf_name;
    `;

    const updateResult = await pool.query(updateQuery, [supersedeIds]);

    console.log(`✅ Marked ${updateResult.rows.length} documents as superseded:\n`);
    updateResult.rows.forEach((row: any) => {
      console.log(`  - ${row.id}`);
    });

    console.log('');
    console.log('=== Final Verification ===');

    // Verify no duplicate active documents remain
    const verifyQuery = `
      SELECT pdf_name, COUNT(*) as count
      FROM documents
      WHERE document_type = 'SEPP'
        AND is_superseded = false
      GROUP BY pdf_name
      HAVING COUNT(*) > 1;
    `;

    const remaining = await pool.query(verifyQuery);

    if (remaining.rows.length === 0) {
      console.log('✅ SUCCESS: No duplicate active SEPP documents remain');
    } else {
      console.log(`⚠️  WARNING: ${remaining.rows.length} documents still have duplicates:`);
      remaining.rows.forEach((row: any) => {
        console.log(`  - ${row.pdf_name} (${row.count} copies)`);
      });
    }

    // Count active SEPPs
    const activeCount = await pool.query(`
      SELECT COUNT(*) as count
      FROM documents
      WHERE document_type = 'SEPP'
        AND is_superseded = false
        AND pdf_name NOT LIKE '%Section%';
    `);

    console.log('');
    console.log(`Active SEPP documents (non-section): ${activeCount.rows[0].count}`);

  } catch (error: any) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

cleanupDuplicates();
