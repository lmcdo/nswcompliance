const fs = require('fs');
const path = require('path');
const { Pool } = require('pg');
require('dotenv').config({ path: path.join(__dirname, '..', '.env.local') });

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

const MIGRATIONS_DIR = path.join(__dirname, '..', 'migrations');
const MIGRATIONS_TABLE = 'migrations_history';

async function ensureMigrationsTable() {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS ${MIGRATIONS_TABLE} (
      id SERIAL PRIMARY KEY,
      filename TEXT UNIQUE NOT NULL,
      executed_at TIMESTAMPTZ DEFAULT NOW(),
      success BOOLEAN NOT NULL,
      error_message TEXT
    )
  `);
}

async function getExecutedMigrations() {
  const result = await pool.query(
    `SELECT filename FROM ${MIGRATIONS_TABLE} WHERE success = true ORDER BY filename`
  );
  return result.rows.map(row => row.filename);
}

async function runMigration(filename) {
  const filepath = path.join(MIGRATIONS_DIR, filename);
  const sql = fs.readFileSync(filepath, 'utf8');

  console.log(`\n🔄 Running migration: ${filename}`);

  try {
    await pool.query('BEGIN');
    await pool.query(sql);
    await pool.query(`
      INSERT INTO ${MIGRATIONS_TABLE} (filename, success)
      VALUES ($1, true)
    `, [filename]);
    await pool.query('COMMIT');

    console.log(`✅ Migration successful: ${filename}`);
    return true;
  } catch (error) {
    await pool.query('ROLLBACK');

    // Log failure to migrations_history
    try {
      await pool.query(`
        INSERT INTO ${MIGRATIONS_TABLE} (filename, success, error_message)
        VALUES ($1, false, $2)
      `, [filename, error.message]);
    } catch (e) {
      // Ignore error logging errors
    }

    console.error(`❌ Migration failed: ${filename}`);
    console.error(`   Error: ${error.message}`);
    return false;
  }
}

async function main() {
  try {
    console.log('📋 Database Migration Runner');
    console.log('================================\n');

    // Ensure migrations history table exists
    await ensureMigrationsTable();
    console.log('✓ Migrations history table ready\n');

    // Get list of already executed migrations
    const executed = await getExecutedMigrations();
    if (executed.length > 0) {
      console.log(`✓ Previously executed migrations: ${executed.length}`);
      executed.forEach(m => console.log(`  - ${m}`));
    } else {
      console.log('ℹ No previous migrations found');
    }

    // Get all migration files
    const files = fs.readdirSync(MIGRATIONS_DIR)
      .filter(f => f.endsWith('.sql') && !f.includes('rollback') && !f.includes('README'))
      .sort();

    // Filter to pending migrations
    const pending = files.filter(f => !executed.includes(f));

    if (pending.length === 0) {
      console.log('\n✨ All migrations up to date. Nothing to run.');
      await pool.end();
      return;
    }

    console.log(`\n📦 Pending migrations: ${pending.length}`);
    pending.forEach(m => console.log(`  - ${m}`));

    // Run each pending migration
    let successCount = 0;
    let failCount = 0;

    for (const filename of pending) {
      const success = await runMigration(filename);
      if (success) {
        successCount++;
      } else {
        failCount++;
        // Stop on first failure
        console.log('\n⛔ Migration failed. Stopping execution.');
        break;
      }
    }

    console.log('\n================================');
    console.log('📊 Migration Summary:');
    console.log(`   Successful: ${successCount}`);
    console.log(`   Failed: ${failCount}`);
    console.log(`   Remaining: ${pending.length - successCount - failCount}`);

    await pool.end();
    process.exit(failCount > 0 ? 1 : 0);

  } catch (error) {
    console.error('❌ Migration runner error:', error);
    await pool.end();
    process.exit(1);
  }
}

main();
