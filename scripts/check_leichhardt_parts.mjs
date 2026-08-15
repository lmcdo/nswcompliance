#!/usr/bin/env node

import pg from 'pg';
import { config } from 'dotenv';

config();

const { Pool } = pg;
const dbUrl = process.env.DATABASE_URL;
const url = new URL(dbUrl);

const pool = new Pool({
  host: url.hostname,
  port: url.port || 5432,
  database: url.pathname.slice(1),
  user: url.username,
  password: url.password,
  ssl: { rejectUnauthorized: false }
});

try {
  // Get all Leichhardt parts grouped by layer
  const result = await pool.query(`
    SELECT
      v2_dcp_part,
      v2_dcp_layer,
      COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
      AND is_current = TRUE
    GROUP BY v2_dcp_part, v2_dcp_layer
    ORDER BY v2_dcp_layer, v2_dcp_part
  `);

  console.log('\nLeichhardt DCP Structure by Layer:\n');

  let currentLayer = null;
  for (const row of result.rows) {
    if (row.v2_dcp_layer !== currentLayer) {
      currentLayer = row.v2_dcp_layer;
      console.log(`\n=== ${currentLayer?.toUpperCase() || 'NULL'} LAYER ===`);
    }
    console.log(`  ${(row.v2_dcp_part || 'NULL').padEnd(45)} ${String(row.count).padStart(4)} provisions`);
  }

  // Check Part C (likely residential) provisions
  console.log('\n\n=== PART C SECTIONS (General Controls - should be zone-specific) ===\n');
  const partC = await pool.query(`
    SELECT
      id,
      v2_dcp_part,
      v2_dcp_layer,
      v2_applicable_zones,
      provision_text
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
      AND is_current = TRUE
      AND v2_dcp_part ILIKE '%Part C%'
    ORDER BY v2_dcp_part, id
    LIMIT 20
  `);

  for (const row of partC.rows) {
    console.log(`\nID ${row.id}: ${row.v2_dcp_part} [Layer: ${row.v2_dcp_layer}]`);
    console.log(`  Zones: ${JSON.stringify(row.v2_applicable_zones)}`);
    console.log(`  Text: ${row.provision_text?.substring(0, 100)}...`);
  }

} catch (error) {
  console.error('Error:', error);
} finally {
  await pool.end();
}
