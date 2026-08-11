/**
 * DB Cleanup Verification Script
 * Run: node scripts/verify_cleanup_state.mjs
 */

import pg from 'pg';
import dotenv from 'dotenv';

// Load env
dotenv.config({ path: '.env.local' });

const pool = new pg.Pool({
  host: process.env.PGHOST,
  database: process.env.PGDATABASE,
  user: process.env.PGUSER,
  password: process.env.PGPASSWORD,
  port: parseInt(process.env.PGPORT || '5432'),
  ssl: process.env.PGHOST?.includes('supabase') ? { rejectUnauthorized: false } : undefined,
});

async function run() {
  const client = await pool.connect();
  const results = {};

  try {
    console.log('\n========================================');
    console.log('DB CLEANUP VERIFICATION - Step 1');
    console.log('========================================\n');

    // 1. Current DB size
    console.log('1. CURRENT DATABASE SIZE');
    console.log('------------------------');
    const sizeResult = await client.query(`SELECT pg_size_pretty(pg_database_size(current_database())) as total_db_size`);
    results.db_size = sizeResult.rows[0].total_db_size;
    console.log(`   Total: ${results.db_size}\n`);

    // 2. Backup table counts
    console.log('2. BACKUP TABLE COUNTS');
    console.log('----------------------');
    results.backup_tables = [];
    const backupTables = [
      { table: 'dcp_general_provisions_backup_r1_fix', expected: 130 },
      { table: 'dcp_general_provisions_corrupted_f1_backup', expected: 7 },
      { table: 'dcp_general_requirements_backup_20251030', expected: 555 },
      { table: 'dcp_general_requirements_old_broad_linking', expected: 189 },
      { table: 'dcp_precinct_boundaries_backup_20251109_152059', expected: 85 },
      { table: 'dcp_precinct_boundaries_backup_polygon', expected: 46 },
      { table: 'dcp_precinct_boundaries_backup_rename_20251109_153810', expected: 5 },
      { table: 'dcp_precinct_requirements_backup_page_fix', expected: 265 },
      { table: 'document_id_backup', expected: 47818 },
    ];

    for (const { table, expected } of backupTables) {
      try {
        const result = await client.query(`SELECT COUNT(*) as cnt FROM ${table}`);
        const actual = parseInt(result.rows[0].cnt);
        const status = actual === expected ? '✓' : '⚠';
        console.log(`   ${status} ${table}: ${actual} rows (expected ${expected})`);
        results.backup_tables.push({ table, actual, expected, exists: true });
      } catch (e) {
        console.log(`   ✗ ${table}: TABLE NOT FOUND`);
        results.backup_tables.push({ table, exists: false });
      }
    }

    // 3. Empty unused tables
    console.log('\n3. EMPTY UNUSED TABLES');
    console.log('----------------------');
    results.empty_tables = [];
    const emptyTables = [
      'categorization_validation',
      'dcp_base_requirements',
      'dcp_precinct_metadata',
      'provision_diagrams',
    ];

    for (const table of emptyTables) {
      try {
        const result = await client.query(`SELECT COUNT(*) as cnt FROM ${table}`);
        const cnt = parseInt(result.rows[0].cnt);
        console.log(`   ${table}: ${cnt} rows`);
        results.empty_tables.push({ table, rows: cnt, exists: true });
      } catch (e) {
        console.log(`   ${table}: TABLE NOT FOUND`);
        results.empty_tables.push({ table, exists: false });
      }
    }

    // 4. Check precinct_boundaries overlap
    console.log('\n4. PRECINCT_BOUNDARIES OVERLAP CHECK');
    console.log('-------------------------------------');
    try {
      const overlapResult = await client.query(`
        SELECT
          pb.precinct_id,
          pb.precinct_name,
          CASE WHEN dpb.precinct_id IS NOT NULL THEN 'MATCH' ELSE 'UNIQUE' END as status
        FROM precinct_boundaries pb
        LEFT JOIN dcp_precinct_boundaries dpb
          ON pb.precinct_id = dpb.precinct_id OR pb.precinct_name = dpb.precinct_name
        ORDER BY pb.precinct_id
      `);
      const matches = overlapResult.rows.filter(r => r.status === 'MATCH').length;
      const total = overlapResult.rows.length;
      console.log(`   ${matches}/${total} rows have matches in dcp_precinct_boundaries`);
      results.precinct_overlap = { matches, total, safe: matches === total };
      if (matches === total) {
        console.log(`   ✓ SAFE TO DROP`);
      } else {
        console.log(`   ⚠ REVIEW NEEDED`);
      }
    } catch (e) {
      console.log(`   TABLE NOT FOUND`);
      results.precinct_overlap = { exists: false };
    }

    // 5. Check regulatory_refs_core subset
    console.log('\n5. REGULATORY_REFS_CORE SUBSET CHECK');
    console.log('-------------------------------------');
    try {
      const coreCount = await client.query(`SELECT COUNT(*) as cnt FROM regulatory_refs_core`);
      const matchCount = await client.query(`
        SELECT COUNT(*) as cnt
        FROM regulatory_refs_core rrc
        WHERE EXISTS (
          SELECT 1 FROM regulatory_refs rr
          WHERE rr.document_id = rrc.document_id
            AND rr.ref_type = rrc.ref_type
            AND rr.ref_number = rrc.ref_number
        )
      `);
      const core = parseInt(coreCount.rows[0].cnt);
      const matches = parseInt(matchCount.rows[0].cnt);
      console.log(`   Core: ${core}, In main: ${matches}`);
      results.refs_core = { core, matches, safe: core === matches };
      if (core === matches) {
        console.log(`   ✓ SAFE TO DROP`);
      } else {
        console.log(`   ⚠ ${core - matches} unique rows`);
      }
    } catch (e) {
      console.log(`   TABLE NOT FOUND`);
      results.refs_core = { exists: false };
    }

    // 6. Check development_pathways
    console.log('\n6. DEVELOPMENT_PATHWAYS');
    console.log('-----------------------');
    try {
      const pathways = await client.query(`SELECT * FROM development_pathways`);
      console.log(`   ${pathways.rows.length} row(s)`);
      results.dev_pathways = { rows: pathways.rows.length, safe: pathways.rows.length <= 1 };
      if (pathways.rows.length <= 1) {
        console.log(`   ✓ SAFE TO DROP (test data)`);
      }
    } catch (e) {
      console.log(`   TABLE NOT FOUND`);
      results.dev_pathways = { exists: false };
    }

    // 7. Tables to keep
    console.log('\n7. TABLES TO KEEP (FEEDBACK SYSTEM)');
    console.log('------------------------------------');
    results.keep_tables = [];
    for (const table of ['requirement_metrics', 'requirement_review_queue']) {
      try {
        const result = await client.query(`SELECT COUNT(*) as cnt FROM ${table}`);
        console.log(`   ${table}: ${result.rows[0].cnt} rows (KEEP)`);
        results.keep_tables.push({ table, rows: parseInt(result.rows[0].cnt) });
      } catch (e) {
        console.log(`   ${table}: TABLE NOT FOUND`);
      }
    }

    console.log('\n========================================');
    console.log('VERIFICATION COMPLETE');
    console.log('========================================\n');

    return results;

  } finally {
    client.release();
    await pool.end();
  }
}

run().catch(err => {
  console.error('Error:', err.message);
  process.exit(1);
});
