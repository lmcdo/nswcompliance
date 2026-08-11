#!/usr/bin/env node
const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '..', '.env.local'), silent: true });

// Import pool manager
const { getPool } = require('../lib/database/pool-manager');
const pool = getPool();

async function checkVersioning() {
  try {
    // Check documents table structure
    const documentsSchema = await pool.query(`
      SELECT column_name, data_type, is_nullable
      FROM information_schema.columns
      WHERE table_name = 'documents'
      ORDER BY ordinal_position;
    `);

    console.log('=== DOCUMENTS TABLE SCHEMA ===');
    documentsSchema.rows.forEach(col => {
      console.log(`  ${col.column_name.padEnd(30)} ${col.data_type.padEnd(20)} nullable: ${col.is_nullable}`);
    });

    // Check if there are any version-related columns
    console.log('\n=== VERSION-RELATED COLUMNS ===');
    const versionCols = documentsSchema.rows.filter(col =>
      col.column_name.includes('version') ||
      col.column_name.includes('date') ||
      col.column_name.includes('effective') ||
      col.column_name.includes('amended')
    );

    if (versionCols.length > 0) {
      versionCols.forEach(col => {
        console.log(`  ${col.column_name}: ${col.data_type}`);
      });
    } else {
      console.log('  NO version-specific columns found');
    }

    // Sample documents to see versioning in practice
    const sampleDocs = await pool.query(`
      SELECT id, document_type, pdf_name,
             regulation_year, amendment_reference, amendment_date,
             last_verified_date, version_status
      FROM documents
      WHERE document_type IN ('SEPP', 'LEP', 'DCP')
      ORDER BY document_type, pdf_name
      LIMIT 15;
    `);

    console.log('\n=== SAMPLE DOCUMENTS (showing versioning data) ===');
    sampleDocs.rows.forEach(doc => {
      console.log(`\n[${doc.document_type}] ${doc.pdf_name}`);
      console.log(`  ID: ${doc.id}`);
      console.log(`  Year: ${doc.regulation_year || 'NULL'}`);
      console.log(`  Amendment: ${doc.amendment_reference || 'NULL'}`);
      console.log(`  Amendment Date: ${doc.amendment_date || 'NULL'}`);
      console.log(`  Last Verified: ${doc.last_verified_date || 'NULL'}`);
      console.log(`  Version Status: ${doc.version_status || 'NULL'}`);
    });

    // Check for SEPP versions in pdf_name
    const seppVersions = await pool.query(`
      SELECT pdf_name, COUNT(*) as provision_count
      FROM documents d
      JOIN regulatory_provisions rp ON rp.document_id = d.id
      WHERE d.document_type = 'SEPP'
      GROUP BY pdf_name
      ORDER BY pdf_name
      LIMIT 20;
    `);

    console.log('\n=== SEPP DOCUMENTS (checking for year/version in names) ===');
    seppVersions.rows.forEach(doc => {
      const yearMatch = doc.pdf_name.match(/20\d{2}/);
      const year = yearMatch ? yearMatch[0] : 'NO YEAR';
      console.log(`  [${year}] ${doc.pdf_name.substring(0, 80)}`);
      console.log(`         Provisions: ${doc.provision_count}`);
    });

    // Check SEPP main documents versioning fields
    const mainSepps = await pool.query(`
      SELECT pdf_name, regulation_year, amendment_reference,
             amendment_date, last_verified_date, version_status
      FROM documents
      WHERE document_type = 'SEPP'
        AND pdf_name NOT LIKE '%Section%'
      ORDER BY pdf_name;
    `);

    console.log('\n=== SEPP MAIN DOCUMENTS - VERSION FIELD USAGE ===');
    mainSepps.rows.forEach(doc => {
      const shortName = doc.pdf_name.replace('State Environmental Planning Policy ', 'SEPP ').substring(0, 60);
      console.log(`\n${shortName}`);
      console.log(`  regulation_year: ${doc.regulation_year || 'NULL'}`);
      console.log(`  amendment_reference: ${doc.amendment_reference || 'NULL'}`);
      console.log(`  amendment_date: ${doc.amendment_date || 'NULL'}`);
      console.log(`  last_verified_date: ${doc.last_verified_date || 'NULL'}`);
      console.log(`  version_status: ${doc.version_status || 'NULL'}`);
    });

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await pool.end();
  }
}

checkVersioning();
