const { Pool } = require('pg');
require('dotenv').config({ path: '.env.local' });

async function checkSeppCounts() {
  const pool = new Pool({ connectionString: process.env.DATABASE_URL });

  // Get all SEPP documents
  const { rows: seppDocs } = await pool.query(`
    SELECT
      document_id,
      COUNT(*) as total_provisions,
      COUNT(*) FILTER (WHERE v2_is_actionable = true) as actionable,
      COUNT(*) FILTER (WHERE v2_is_actionable = false) as non_actionable,
      COUNT(DISTINCT v2_topic) as unique_topics,
      COUNT(DISTINCT v2_part) as unique_parts
    FROM regulatory_provisions
    WHERE document_id LIKE '%SEPP%' OR document_id LIKE '%State_Environmental_Planning_Policy%'
    GROUP BY document_id
    ORDER BY total_provisions DESC
  `);

  console.log('=== SEPP Documents in Database ===\n');

  seppDocs.forEach(doc => {
    const shortName = doc.document_id
      .replace('State_Environmental_Planning_Policy_', '')
      .replace('__NSW_Legislation', '')
      .replace(/_/g, ' ');

    console.log(`📄 ${shortName}`);
    console.log(`   Total: ${doc.total_provisions} provisions`);
    console.log(`   Actionable: ${doc.actionable} | Non-actionable: ${doc.non_actionable}`);
    console.log(`   Topics: ${doc.unique_topics} | Parts: ${doc.unique_parts}`);
    console.log();
  });

  // Get breakdown by topic for Exempt & Complying
  const { rows: exemptTopics } = await pool.query(`
    SELECT
      v2_topic,
      v2_part,
      COUNT(*) as count,
      COUNT(*) FILTER (WHERE v2_is_actionable = true) as actionable
    FROM regulatory_provisions
    WHERE document_id = 'State_Environmental_Planning_Policy_Exempt_and_Complying_Development_Codes_2008__NSW_Legislation'
      AND v2_topic IS NOT NULL
    GROUP BY v2_topic, v2_part
    ORDER BY v2_part, count DESC
  `);

  console.log('=== SEPP Exempt & Complying Development: Topics Breakdown ===\n');

  let currentPart = null;
  exemptTopics.forEach(t => {
    if (t.v2_part !== currentPart) {
      console.log(`\n[Part ${t.v2_part}]`);
      currentPart = t.v2_part;
    }
    console.log(`  ${t.v2_topic.padEnd(20)} ${t.count.toString().padStart(3)} provisions (${t.actionable} actionable)`);
  });

  // Get total counts
  const { rows: totals } = await pool.query(`
    SELECT
      COUNT(*) as total_sepp,
      COUNT(DISTINCT document_id) as total_sepp_docs
    FROM regulatory_provisions
    WHERE document_id LIKE '%SEPP%' OR document_id LIKE '%State_Environmental_Planning_Policy%'
  `);

  console.log('\n=== Summary ===');
  console.log(`Total SEPP provisions: ${totals[0].total_sepp}`);
  console.log(`Total SEPP documents: ${totals[0].total_sepp_docs}`);

  process.exit(0);
}

checkSeppCounts().catch(err => {
  console.error(err);
  process.exit(1);
});
