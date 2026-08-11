#!/usr/bin/env tsx
import Anthropic from '@anthropic-ai/sdk';
import { getPool } from '../lib/database/pool-manager.js';
import { config } from 'dotenv';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
config({ path: path.join(__dirname, '..', '.env.local') });

const pool = getPool();

async function test() {
  console.log('=== Minimal Extraction Test ===\n');

  // Get one provision
  const provision = await pool.query(`
    SELECT id, provision_text, pdf_page
    FROM regulatory_provisions
    WHERE document_id IN (SELECT id FROM documents WHERE document_type = 'SEPP')
      AND v2_is_actionable = true
    LIMIT 1
  `);

  console.log(`Found provision #${provision.rows[0].id}`);
  console.log(`Text: ${provision.rows[0].provision_text.substring(0, 100)}...\n`);

  // Insert a test requirement
  const insert = await pool.query(`
    INSERT INTO sepp_structured_requirements (
      provision_id,
      requirement_category,
      source_clause,
      extraction_confidence
    ) VALUES ($1, 'procedure', 'Test Clause', 0.95)
    RETURNING id
  `, [provision.rows[0].id]);

  console.log(`✅ Inserted requirement ID: ${insert.rows[0].id}`);

  // Verify it's there
  const count = await pool.query('SELECT COUNT(*) FROM sepp_structured_requirements');
  console.log(`Total requirements in DB: ${count.rows[0].count}`);

  // Clean up
  await pool.query('DELETE FROM sepp_structured_requirements WHERE id = $1', [insert.rows[0].id]);
  console.log('✅ Cleaned up test data');

  await pool.end();
}

test();
