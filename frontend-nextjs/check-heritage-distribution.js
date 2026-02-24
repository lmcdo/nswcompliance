const { Pool } = require('pg');
require('dotenv').config({ path: '.env.local' });

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

async function checkHeritageDistribution() {
  // Check heritage provisions by council and topic
  const result = await pool.query(`
    SELECT
      CASE
        WHEN document_id LIKE 'Ashfield%' THEN 'Ashfield'
        WHEN document_id LIKE 'Leichhardt%' THEN 'Leichhardt'
        WHEN document_id LIKE 'Marrickville%' THEN 'Marrickville'
        ELSE 'Other'
      END as council,
      v2_topic,
      v2_dcp_part,
      COUNT(*) as provision_count
    FROM regulatory_provisions
    WHERE v2_marker = 'heritage'
      AND v2_is_actionable = true
      AND document_id IS NOT NULL
    GROUP BY council, v2_topic, v2_dcp_part
    ORDER BY council, provision_count DESC
  `);

  console.log('Heritage provisions distribution by council, topic, and part:\n');

  let currentCouncil = '';
  result.rows.forEach(row => {
    if (row.council !== currentCouncil) {
      currentCouncil = row.council;
      console.log(`\n=== ${currentCouncil.toUpperCase()} ===`);
    }
    console.log(`  ${row.v2_topic || '(no topic)'} | Part ${row.v2_dcp_part || '?'}: ${row.provision_count} provisions`);
  });

  // Get totals
  const totals = await pool.query(`
    SELECT
      CASE
        WHEN document_id LIKE 'Ashfield%' THEN 'Ashfield'
        WHEN document_id LIKE 'Leichhardt%' THEN 'Leichhardt'
        WHEN document_id LIKE 'Marrickville%' THEN 'Marrickville'
        ELSE 'Other'
      END as council,
      COUNT(*) as total
    FROM regulatory_provisions
    WHERE v2_marker = 'heritage'
      AND v2_is_actionable = true
    GROUP BY council
    ORDER BY total DESC
  `);

  console.log('\n\n--- TOTAL HERITAGE PROVISIONS ---');
  totals.rows.forEach(row => {
    console.log(`${row.council}: ${row.total} total`);
  });

  // Check general vs HCA-specific breakdown for each council
  console.log('\n\n--- GENERAL vs HCA-SPECIFIC BREAKDOWN ---');

  const councils = ['Ashfield', 'Leichhardt', 'Marrickville'];
  for (const council of councils) {
    const breakdown = await pool.query(`
      SELECT
        CASE
          WHEN v2_heritage_hca IS NULL THEN 'General (all heritage)'
          ELSE 'HCA-specific'
        END as scope,
        COUNT(*) as count
      FROM regulatory_provisions
      WHERE v2_marker = 'heritage'
        AND v2_is_actionable = true
        AND (document_id LIKE $1 OR document_id LIKE $2)
      GROUP BY scope
      ORDER BY count DESC
    `, [`${council}%`, `%${council}%`]);

    console.log(`\n${council}:`);
    breakdown.rows.forEach(row => {
      console.log(`  ${row.scope}: ${row.count} provisions`);
    });
  }

  // Show sample HCA tags for Marrickville
  console.log('\n\n--- SAMPLE HCA TAGS (Marrickville) ---');
  const hcaSample = await pool.query(`
    SELECT DISTINCT v2_heritage_hca, COUNT(*) as count
    FROM regulatory_provisions
    WHERE v2_marker = 'heritage'
      AND v2_is_actionable = true
      AND document_id LIKE '%Marrickville%'
      AND v2_heritage_hca IS NOT NULL
    GROUP BY v2_heritage_hca
    ORDER BY count DESC
    LIMIT 10
  `);

  hcaSample.rows.forEach(row => {
    console.log(`  ${row.v2_heritage_hca}: ${row.count} provisions`);
  });

  pool.end();
}

checkHeritageDistribution().catch(err => {
  console.error(err);
  pool.end();
  process.exit(1);
});
