#!/usr/bin/env node

/**
 * Fix heritage provision layer tagging
 * Issue: Heritage provisions are tagged as 'generic' when they should be 'condition'
 */

const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

async function main() {
  // Read database URL from env
  require('dotenv').config({ path: path.join(__dirname, '../frontend-nextjs/.env.local') });

  const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false }
  });

  const client = await pool.connect();

  try {
    console.log('Connected to database');
    console.log('\n=== BEFORE FIX ===');

    // Show current state
    const before = await client.query(`
      SELECT
        v2_dcp_layer,
        COUNT(*) as count
      FROM regulatory_provisions
      WHERE v2_topic = 'heritage'
        AND document_id LIKE '%Leichhardt%'
      GROUP BY v2_dcp_layer
      ORDER BY count DESC
    `);

    console.table(before.rows);

    // Update heritage provisions to condition layer
    console.log('\n=== APPLYING FIX ===');
    const result = await client.query(`
      UPDATE regulatory_provisions
      SET v2_dcp_layer = 'condition'
      WHERE v2_topic = 'heritage'
        AND v2_dcp_layer = 'generic'
        AND document_id LIKE '%Leichhardt%'
        AND v2_is_actionable = true
    `);

    console.log(`Updated ${result.rowCount} provisions from generic to condition layer`);

    // Show after state
    console.log('\n=== AFTER FIX ===');
    const after = await client.query(`
      SELECT
        v2_dcp_layer,
        COUNT(*) as count
      FROM regulatory_provisions
      WHERE v2_topic = 'heritage'
        AND document_id LIKE '%Leichhardt%'
      GROUP BY v2_dcp_layer
      ORDER BY count DESC
    `);

    console.table(after.rows);

    // Show sample of updated provisions
    console.log('\n=== SAMPLE UPDATED PROVISIONS ===');
    const sample = await client.query(`
      SELECT
        v2_dcp_part,
        v2_marker,
        v2_dcp_layer,
        LEFT(provision_text, 80) as text_preview
      FROM regulatory_provisions
      WHERE v2_topic = 'heritage'
        AND v2_dcp_layer = 'condition'
        AND document_id LIKE '%Leichhardt%'
      LIMIT 5
    `);

    console.table(sample.rows);

    console.log('\n✅ Heritage layer tagging fixed successfully');

  } catch (error) {
    console.error('❌ Error:', error);
    process.exit(1);
  } finally {
    client.release();
    await pool.end();
  }
}

main();
