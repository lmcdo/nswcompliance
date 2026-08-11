#!/usr/bin/env tsx
/**
 * Extract Existing SEPP Amendment Data
 *
 * Queries database for existing amendment references and dates,
 * populates research template with real data.
 */

import { getPool } from '@/lib/database/pool-manager';

const pool = getPool();

const seppPatterns = [
  { name: 'Housing SEPP 2021', pattern: '%Housing%2021%', slug: 'sepp-housing-2021' },
  { name: 'Transport & Infrastructure SEPP 2021', pattern: '%Transport%Infrastructure%2021%', slug: 'sepp-transport-infrastructure-2021' },
  { name: 'Biodiversity & Conservation SEPP 2021', pattern: '%Biodiversity%Conservation%2021%', slug: 'sepp-biodiversity-conservation-2021' },
  { name: 'Resilience & Hazards SEPP 2021', pattern: '%Resilience%Hazards%2021%', slug: 'sepp-resilience-hazards-2021' },
  { name: 'Planning Systems SEPP 2021', pattern: '%Planning Systems%2021%', slug: 'sepp-planning-systems-2021' },
  { name: 'Industry & Employment SEPP 2021', pattern: '%Industry%Employment%2021%', slug: 'sepp-industry-employment-2021' },
  { name: 'Primary Production SEPP 2021', pattern: '%Primary Production%2021%', slug: 'sepp-primary-production-2021' },
  { name: 'Sustainable Buildings SEPP 2022', pattern: '%Sustainable Buildings%2022%', slug: 'sepp-sustainable-buildings-2022' },
  { name: 'Exempt & Complying Development Codes SEPP 2008', pattern: '%Exempt%Complying%2008%', slug: 'sepp-exempt-complying-codes-2008' }
];

async function extractAmendments() {
  try {
    console.log('=== Extracting Existing SEPP Amendment Data ===\n');

    const results: any[] = [];

    for (const sepp of seppPatterns) {
      const query = `
        SELECT
          id,
          pdf_name,
          amendment_reference,
          amendment_date,
          amending_epis,
          major_amendments,
          last_verified_date,
          consolidated_as_of_date
        FROM documents
        WHERE document_type = 'SEPP'
          AND is_superseded = false
          AND pdf_name LIKE $1
        LIMIT 1;
      `;

      const result = await pool.query(query, [sepp.pattern]);

      if (result.rows.length > 0) {
        const doc = result.rows[0];

        console.log(`${sepp.name}:`);
        console.log(`  ID: ${doc.id}`);
        console.log(`  Amendment Ref: ${doc.amendment_reference || 'NULL'}`);
        console.log(`  Amendment Date: ${doc.amendment_date || 'NULL'}`);
        console.log(`  Amending EPIs: ${doc.amending_epis || 'NULL'}`);
        console.log(`  Major Amendments: ${JSON.stringify(doc.major_amendments) || 'NULL'}`);
        console.log(`  Last Verified: ${doc.last_verified_date || 'NULL'}`);
        console.log(`  Consolidated As Of: ${doc.consolidated_as_of_date || 'NULL'}`);
        console.log('');

        results.push({
          name: sepp.name,
          slug: sepp.slug,
          document_id: doc.id,
          amendment_reference: doc.amendment_reference,
          amendment_date: doc.amendment_date,
          amending_epis: doc.amending_epis,
          major_amendments: doc.major_amendments,
          last_verified_date: doc.last_verified_date,
          consolidated_as_of_date: doc.consolidated_as_of_date
        });
      } else {
        console.log(`${sepp.name}: NOT FOUND`);
        console.log('');
      }
    }

    console.log('=== Summary ===');
    console.log(`Total SEPPs found: ${results.length}/9`);
    console.log(`With amendment_reference: ${results.filter(r => r.amendment_reference).length}`);
    console.log(`With amending_epis: ${results.filter(r => r.amending_epis).length}`);
    console.log(`With major_amendments: ${results.filter(r => r.major_amendments && r.major_amendments.length > 0).length}`);

    console.log('\n=== Detailed Amendment Data ===');
    results.forEach(r => {
      if (r.amendment_reference || r.amending_epis || (r.major_amendments && r.major_amendments.length > 0)) {
        console.log(`\n${r.name}:`);
        if (r.amendment_reference) console.log(`  Reference: ${r.amendment_reference}`);
        if (r.amending_epis) console.log(`  EPIs: ${r.amending_epis}`);
        if (r.major_amendments && r.major_amendments.length > 0) {
          console.log(`  Major Amendments: ${JSON.stringify(r.major_amendments, null, 2)}`);
        }
      }
    });

  } catch (error: any) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

extractAmendments();
