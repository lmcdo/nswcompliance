const { Pool } = require('pg');
const db = new Pool({ connectionString: process.env.DATABASE_URL });

async function check() {
  const workTypes = ['Deck', 'Fence', 'Pool', 'Garage'];

  for (const type of workTypes) {
    const { rows } = await getPool().query(`
      SELECT v2_topic, provision_text, v2_part
      FROM regulatory_provisions
      WHERE document_id = 'State_Environmental_Planning_Policy_Exempt_and_Complying_Development_Codes_2008__NSW_Legislation'
        AND v2_topic = $1
        AND v2_is_actionable = true
      LIMIT 3
    `, [type]);

    console.log(`\n=== ${type} (${rows.length} samples) ===`);
    rows.forEach((r, i) => {
      const text = r.provision_text.substring(0, 200).replace(/\n/g, ' ');
      console.log(`${i+1}. [Part ${r.v2_part}] ${text}...`);
    });
  }

  // Check what topics exist
  const { rows: topics } = await pool.query(`
    SELECT v2_topic, COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id = 'State_Environmental_Planning_Policy_Exempt_and_Complying_Development_Codes_2008__NSW_Legislation'
      AND v2_is_actionable = true
    GROUP BY v2_topic
    ORDER BY count DESC
  `);

  console.log('\n=== All v2_topics in SEPP ===');
  topics.forEach(t => console.log(`${t.v2_topic}: ${t.count} provisions`));

  process.exit(0);
}

check().catch(console.error);
