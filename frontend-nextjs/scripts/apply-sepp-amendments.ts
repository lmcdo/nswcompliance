#!/usr/bin/env tsx
/**
 * Apply SEPP Amendments to Database
 *
 * Reads sepp-amendments-research.json and updates the documents table
 * with amendment information for each SEPP.
 */

import { getPool } from '@/lib/database/pool-manager';
import * as fs from 'fs';
import * as path from 'path';

const pool = getPool();

async function applyAmendments() {
  try {
    console.log('=== Applying SEPP Amendments to Database ===\n');

    // Read research data
    const researchPath = path.join(__dirname, 'sepp-amendments-research.json');
    const research = JSON.parse(fs.readFileSync(researchPath, 'utf8'));

    console.log(`Research period: ${research.research_period.from} to ${research.research_period.to}`);
    console.log('');

    // SEPP to document ID mapping
    const seppPatterns: Record<string, string> = {
      'sepp-housing-2021': '%Housing%2021%',
      'sepp-transport-infrastructure-2021': '%Transport%Infrastructure%2021%',
      'sepp-biodiversity-conservation-2021': '%Biodiversity%Conservation%2021%',
      'sepp-resilience-hazards-2021': '%Resilience%Hazards%2021%',
      'sepp-planning-systems-2021': '%Planning Systems%2021%',
      'sepp-industry-employment-2021': '%Industry%Employment%2021%',
      'sepp-primary-production-2021': '%Primary Production%2021%',
      'sepp-sustainable-buildings-2022': '%Sustainable Buildings%2022%',
      'sepp-exempt-complying-codes-2008': '%Exempt%Complying%2008%'
    };

    let updatedCount = 0;
    let skippedCount = 0;

    for (const sepp of research.sepps) {
      console.log(`Processing: ${sepp.name}`);

      // Skip if no amendments or pending manual research
      if (sepp.amendments_found.length === 0 || sepp.status === 'PENDING_MANUAL_RESEARCH') {
        console.log(`  ⏭️  Skipped (${sepp.status || 'no amendments'})`);
        console.log('');
        skippedCount++;
        continue;
      }

      // Find document ID
      const pattern = seppPatterns[sepp.slug];
      if (!pattern) {
        console.log(`  ❌ No pattern mapping for ${sepp.slug}`);
        console.log('');
        continue;
      }

      const docQuery = `
        SELECT id, consolidated_as_of_date, amending_epis, major_amendments
        FROM documents
        WHERE document_type = 'SEPP'
          AND is_superseded = false
          AND pdf_name LIKE $1
        LIMIT 1;
      `;

      const docResult = await pool.query(docQuery, [pattern]);

      if (docResult.rows.length === 0) {
        console.log(`  ❌ Document not found`);
        console.log('');
        continue;
      }

      const doc = docResult.rows[0];
      console.log(`  Document ID: ${doc.id}`);

      // Prepare amendment data
      const amendingEPIs = sepp.amendments_found.map((a: any) => a.epi);
      const majorAmendments = sepp.amendments_found.map((a: any) => ({
        epi: a.epi,
        effective_date: a.effective_date,
        description: a.description,
        affects_provisions: a.affects_provisions || false,
        note: a.note || null
      }));

      // Get the most recent effective date as new consolidated_as_of_date
      const dates = sepp.amendments_found
        .map((a: any) => new Date(a.effective_date))
        .sort((a: Date, b: Date) => b.getTime() - a.getTime());
      const mostRecentDate = dates[0];

      // Update document
      const updateQuery = `
        UPDATE documents
        SET
          amending_epis = $1,
          major_amendments = $2,
          consolidated_as_of_date = $3,
          last_verified_date = CURRENT_DATE,
          next_check_date = CURRENT_DATE + INTERVAL '90 days',
          version_status = 'current'
        WHERE id = $4
        RETURNING id, consolidated_as_of_date, next_check_date;
      `;

      const updateResult = await pool.query(updateQuery, [
        amendingEPIs,
        JSON.stringify(majorAmendments),
        mostRecentDate,
        doc.id
      ]);

      if (updateResult.rows.length > 0) {
        const updated = updateResult.rows[0];
        console.log(`  ✅ Updated`);
        console.log(`     - ${amendingEPIs.length} EPIs recorded`);
        console.log(`     - Consolidated as of: ${mostRecentDate.toLocaleDateString()}`);
        console.log(`     - Next check: ${new Date(updated.next_check_date).toLocaleDateString()}`);
        updatedCount++;
      }

      console.log('');
    }

    console.log('=== Summary ===');
    console.log(`Updated: ${updatedCount} SEPPs`);
    console.log(`Skipped: ${skippedCount} SEPPs (no amendments or pending manual research)`);

    if (updatedCount > 0) {
      console.log('\n✅ SEPP version tracking updated successfully');
      console.log('   All updated SEPPs now have current amendment history');
    }

  } catch (error: any) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

applyAmendments();
