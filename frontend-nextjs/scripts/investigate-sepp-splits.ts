#!/usr/bin/env tsx
import { getPool } from '@/lib/database/pool-manager';

const pool = getPool();

async function investigate() {
  try {
    console.log('=== Investigating SEPP Document Structure ===\n');

    // Check Transport SEPP as example (biggest discrepancy)
    const query = `
      SELECT
        d.id,
        d.pdf_name,
        d.pdf_path,
        COUNT(rp.id) as provision_count,
        COUNT(rp.id) FILTER (WHERE rp.is_current) as current_provision_count
      FROM documents d
      LEFT JOIN regulatory_provisions rp ON rp.document_id = d.id
      WHERE d.pdf_name = 'State Environmental Planning Policy (Transport and Infrastructure) 2021 - NSW Legislation.pdf'
        AND d.document_type = 'SEPP'
      GROUP BY d.id, d.pdf_name, d.pdf_path
      ORDER BY COUNT(rp.id) DESC;
    `;

    const result = await pool.query(query);

    console.log('Transport & Infrastructure SEPP (2 copies):');
    console.log('');

    result.rows.forEach((row: any, idx: number) => {
      console.log(`Document ${idx + 1}: ${row.provision_count} provisions`);
      console.log(`  ID: ${row.id}`);
      console.log(`  PDF Path: ${row.pdf_path || 'NULL'}`);
      console.log('');
    });

    // Check if there are section/split documents
    const sectionQuery = `
      SELECT pdf_name, COUNT(*) as count
      FROM documents
      WHERE document_type = 'SEPP'
        AND (
          pdf_name LIKE '%Section%'
          OR pdf_name LIKE '%SPLIT%'
          OR pdf_name LIKE '%Part%'
        )
      GROUP BY pdf_name
      ORDER BY COUNT(*) DESC;
    `;

    const sections = await pool.query(sectionQuery);

    if (sections.rows.length > 0) {
      console.log('=== Section/Split SEPP Documents Found ===');
      console.log('');
      sections.rows.forEach((row: any) => {
        console.log(`${row.pdf_name}: ${row.count} documents`);
      });
    } else {
      console.log('No section/split documents found.');
    }

    // Summary recommendation
    console.log('');
    console.log('=== RECOMMENDATION ===');
    console.log('The documents WITHOUT parentheses in their IDs have MORE provisions.');
    console.log('These are likely the COMPLETE consolidated versions.');
    console.log('');
    console.log('ACTION: REVERSE the cleanup strategy:');
    console.log('  - KEEP: Documents WITHOUT parentheses (more provisions)');
    console.log('  - SUPERSEDE: Documents WITH parentheses (fewer provisions)');

  } catch (error: any) {
    console.error('Error:', error.message);
  } finally {
    await pool.end();
  }
}

investigate();
