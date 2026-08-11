#!/usr/bin/env tsx
/**
 * Test SEPP Extraction with Explicit Transaction Control
 *
 * FIX: Uses single database client with explicit BEGIN/COMMIT
 * instead of pool.query() which creates new connections
 */

import Anthropic from '@anthropic-ai/sdk';
import { getPool } from '../lib/database/pool-manager.js';
import { config } from 'dotenv';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
config({ path: path.join(__dirname, '..', '.env.local') });

const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY;
const MODEL = 'claude-sonnet-4-5-20250929';

const client = new Anthropic({ apiKey: ANTHROPIC_API_KEY });
const pool = getPool();

async function extractRequirement(provision: any) {
  const prompt = `Extract structured requirements from this SEPP provision.

Provision: ${provision.provision_text}

Return exclusion triggers, numeric standards, or procedural requirements.`;

  try {
    const response = await client.messages.create({
      model: MODEL,
      max_tokens: 2048,
      messages: [{ role: 'user', content: prompt }]
    });

    // Simplified extraction - just return a mock requirement
    return [{
      requirement_category: 'procedure',
      source_clause: 'Test',
      extraction_confidence: 0.95
    }];
  } catch (error) {
    console.error('API error:', error);
    return [];
  }
}

async function main() {
  console.log('=== Testing Extraction with Transaction Control ===\n');

  // Get a SINGLE client from pool
  const dbClient = await pool.connect();

  try {
    // Start explicit transaction
    await dbClient.query('BEGIN');
    console.log('✅ Transaction started\n');

    // Fetch 2 provisions
    const provisions = await dbClient.query(`
      SELECT rp.id, rp.provision_text, rp.pdf_page
      FROM regulatory_provisions rp
      JOIN documents d ON rp.document_id = d.id
      WHERE d.document_type = 'SEPP'
        AND rp.v2_is_actionable = true
      LIMIT 2
    `);

    console.log(`Found ${provisions.rows.length} provisions\n`);

    let totalInserted = 0;

    for (const provision of provisions.rows) {
      console.log(`[${provision.id}] Extracting...`);

      const requirements = await extractRequirement(provision);

      console.log(`  Extracted ${requirements.length} requirement(s)`);

      // Insert using same client
      for (const req of requirements) {
        const result = await dbClient.query(`
          INSERT INTO sepp_structured_requirements (
            provision_id,
            requirement_category,
            source_clause,
            extraction_confidence
          ) VALUES ($1, $2, $3, $4)
          RETURNING id
        `, [provision.id, req.requirement_category, req.source_clause, req.extraction_confidence]);

        console.log(`  ✅ Inserted requirement ID: ${result.rows[0].id}`);
        totalInserted++;
      }
    }

    // EXPLICIT COMMIT
    await dbClient.query('COMMIT');
    console.log(`\n✅ TRANSACTION COMMITTED - ${totalInserted} requirements saved\n`);

    // Verify in same client
    const count1 = await dbClient.query('SELECT COUNT(*) FROM sepp_structured_requirements');
    console.log(`Count (same client): ${count1.rows[0].count}`);

    // Verify in new connection
    const count2 = await pool.query('SELECT COUNT(*) FROM sepp_structured_requirements');
    console.log(`Count (new connection): ${count2.rows[0].count}`);

    if (count2.rows[0].count > 0) {
      console.log('\n🎉 SUCCESS! Data persisted!\n');

      // Cleanup
      await pool.query('DELETE FROM sepp_structured_requirements WHERE source_clause = $1', ['Test']);
      console.log('✅ Cleaned up test data');
    } else {
      console.log('\n❌ FAILED - Data still not persisting\n');
    }

  } catch (error) {
    await dbClient.query('ROLLBACK');
    console.error('❌ Error, transaction rolled back:', error);
  } finally {
    dbClient.release();
    await pool.end();
  }
}

main();
