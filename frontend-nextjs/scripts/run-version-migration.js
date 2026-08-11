#!/usr/bin/env node
const { Pool } = require('pg');
const path = require('path');
const fs = require('fs');
require('dotenv').config({ path: path.join(__dirname, '..', '.env.local'), silent: true });

// Standalone script - direct Pool usage is acceptable (same pattern as run-migrations.js)
const pool = new Pool({ connectionString: process.env.DATABASE_URL });

async function runMigration() {
  try {
    console.log('=== SEPP Version Tracking Migration ===\n');

    // Read migration file
    const migrationPath = path.join(__dirname, '..', '..', 'migrations', '006_add_sepp_version_tracking.sql');
    const migrationSQL = fs.readFileSync(migrationPath, 'utf8');

    console.log('Running migration: 006_add_sepp_version_tracking.sql\n');

    // Execute migration
    const result = await pool.query(migrationSQL);

    console.log('\n✅ Migration completed successfully!\n');

    // Verify columns were added
    const verifyQuery = `
      SELECT
        column_name,
        data_type,
        is_nullable,
        column_default
      FROM information_schema.columns
      WHERE table_name = 'documents'
        AND column_name IN ('consolidated_as_of_date', 'consolidation_url', 'amending_epis',
                            'major_amendments', 'next_check_date', 'is_superseded')
      ORDER BY ordinal_position;
    `;

    const columns = await pool.query(verifyQuery);

    console.log('=== New Columns Added ===');
    columns.rows.forEach(col => {
      console.log(`  ${col.column_name.padEnd(25)} ${col.data_type.padEnd(20)} nullable: ${col.is_nullable}`);
    });

    // Check indexes
    const indexQuery = `
      SELECT indexname, indexdef
      FROM pg_indexes
      WHERE tablename = 'documents'
        AND indexname LIKE 'idx_documents_%version%'
           OR indexname LIKE 'idx_documents_%check%';
    `;

    const indexes = await pool.query(indexQuery);

    console.log('\n=== Indexes Created ===');
    if (indexes.rows.length > 0) {
      indexes.rows.forEach(idx => {
        console.log(`  ${idx.indexname}`);
      });
    } else {
      console.log('  (checking with alternative query...)');

      const allIndexes = await pool.query(`
        SELECT indexname
        FROM pg_indexes
        WHERE tablename = 'documents'
        ORDER BY indexname;
      `);

      console.log('\n  All document indexes:');
      allIndexes.rows.forEach(idx => {
        console.log(`    ${idx.indexname}`);
      });
    }

    // Count SEPPs that will benefit from versioning
    const seppCount = await pool.query(`
      SELECT COUNT(*) as count
      FROM documents
      WHERE document_type = 'SEPP'
        AND is_superseded = false;
    `);

    console.log(`\n=== Ready for Version Tracking ===`);
    console.log(`  ${seppCount.rows[0].count} SEPP documents ready for metadata population`);

  } catch (error) {
    console.error('\n❌ Migration failed:');
    console.error(error.message);
    console.error('\nFull error:', error);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

runMigration();
