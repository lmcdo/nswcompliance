#!/usr/bin/env tsx
import { getPool } from '@/lib/database/pool-manager';

const pool = getPool();

async function verifyProvisions() {
  try {
    console.log('=== Verifying Provision Counts Before Cleanup ===\n');

    const duplicatePairs = [
      {
        keep: 'State_Environmental_Planning_Policy_(Biodiversity_and_Conservation)_2021___NSW_Legislation',
        supersede: 'State_Environmental_Planning_Policy_Biodiversity_and_Conservation_2021__NSW_Legislation'
      },
      {
        keep: 'State_Environmental_Planning_Policy_(Industry_and_Employment)_2021___NSW_Legislation',
        supersede: 'State_Environmental_Planning_Policy_Industry_and_Employment_2021__NSW_Legislation'
      },
      {
        keep: 'State_Environmental_Planning_Policy_(Planning_Systems)_2021___NSW_Legislation',
        supersede: 'State_Environmental_Planning_Policy_Planning_Systems_2021__NSW_Legislation'
      },
      {
        keep: 'State_Environmental_Planning_Policy_(Primary_Production)_2021___NSW_Legislation',
        supersede: 'State_Environmental_Planning_Policy_Primary_Production_2021__NSW_Legislation'
      },
      {
        keep: 'State_Environmental_Planning_Policy_(Resilience_and_Hazards)_2021___NSW_Legislation',
        supersede: 'State_Environmental_Planning_Policy_Resilience_and_Hazards_2021__NSW_Legislation'
      },
      {
        keep: 'State_Environmental_Planning_Policy_(Sustainable_Buildings)_2022___NSW_Legislation',
        supersede: 'State_Environmental_Planning_Policy_Sustainable_Buildings_2022__NSW_Legislation'
      },
      {
        keep: 'State_Environmental_Planning_Policy_(Transport_and_Infrastructure)_2021___NSW_Legislation',
        supersede: 'State_Environmental_Planning_Policy_Transport_and_Infrastructure_2021__NSW_Legislation'
      }
    ];

    let allSafe = true;

    for (const pair of duplicatePairs) {
      // NO is_current FILTER, DELIBERATELY. This counts EVERY provision attached
      // to each document, superseded ones included, because the count is what
      // decides which of two duplicate documents to keep and which to supersede.
      // Filtering to is_current = TRUE would make a document whose provisions had
      // already been marked non-current look empty, and the script would then
      // recommend superseding the wrong one — losing the larger corpus.
      // Currency is the caller's question here, not this query's.
      const countQuery = `
        SELECT
          d.id,
          d.pdf_name,
          COUNT(rp.id) as provision_count
        FROM documents d
        LEFT JOIN regulatory_provisions rp ON rp.document_id = d.id
        WHERE d.id IN ($1, $2)
        GROUP BY d.id, d.pdf_name
        ORDER BY d.id;
      `;

      const result = await pool.query(countQuery, [pair.keep, pair.supersede]);

      const keepDoc = result.rows.find((r: any) => r.id === pair.keep);
      const supersedeDoc = result.rows.find((r: any) => r.id === pair.supersede);

      const keepCount = keepDoc?.provision_count || 0;
      const supersedeCount = supersedeDoc?.provision_count || 0;

      const status = keepCount === 0 && supersedeCount > 0 ? '❌ PROBLEM' :
                     keepCount > 0 && supersedeCount === 0 ? '✅ SAFE' :
                     keepCount === 0 && supersedeCount === 0 ? '⚠️  BOTH EMPTY' :
                     '❓ BOTH HAVE PROVISIONS';

      console.log(`${status}: ${keepDoc?.pdf_name || pair.keep}`);
      console.log(`  KEEP document (${pair.keep.substring(0, 40)}...): ${keepCount} provisions`);
      console.log(`  SUPERSEDE document (${pair.supersede.substring(0, 40)}...): ${supersedeCount} provisions`);
      console.log('');

      if (keepCount === 0 && supersedeCount > 0) {
        allSafe = false;
        console.log('  ⚠️  WARNING: Document to KEEP has 0 provisions, but SUPERSEDE has provisions!');
        console.log('  RECOMMENDATION: Swap which document to keep, or migrate provisions first.');
        console.log('');
      }
    }

    console.log('=== Summary ===');
    if (allSafe) {
      console.log('✅ Safe to proceed with cleanup - KEEP documents have provisions or both are empty');
    } else {
      console.log('❌ UNSAFE to proceed - Need to migrate provisions or swap KEEP/SUPERSEDE choices');
    }

  } catch (error: any) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

verifyProvisions();
