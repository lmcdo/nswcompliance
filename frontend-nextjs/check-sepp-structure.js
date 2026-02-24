const { Pool } = require('pg');
require('dotenv').config({ path: '.env.local' });

const pool = new Pool({ connectionString: process.env.DATABASE_URL });

async function check() {
  // Check table schema
  const { rows: columns } = await pool.query(`
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'regulatory_provisions'
      AND table_schema = 'public'
    ORDER BY ordinal_position
  `);

  console.log('=== SEPP Provisions Schema ===');
  columns.forEach(c => console.log(`${c.column_name.padEnd(30)} ${c.data_type}`));

  // Sample SEPP provisions
  const { rows: samples } = await pool.query(`
    SELECT
      id,
      v2_topic,
      v2_part,
      v2_is_actionable,
      pdf_page,
      provision_text
    FROM regulatory_provisions
    WHERE document_id = 'State_Environmental_Planning_Policy_Exempt_and_Complying_Development_Codes_2008__NSW_Legislation'
      AND v2_topic IN ('Deck', 'Fence', 'Pool', 'Carport')
      AND v2_is_actionable = true
    ORDER BY v2_topic, id
    LIMIT 12
  `);

  console.log('\n=== Sample SEPP Provisions (first 200 chars) ===');
  samples.forEach(s => {
    const text = s.provision_text.substring(0, 200).replace(/\n/g, ' ');
    console.log(`\n[${s.v2_topic}] Part ${s.v2_part} | Page ${s.pdf_page}`);
    console.log(`  ${text}...`);
  });

  // Check for any structured fields
  const { rows: structured } = await pool.query(`
    SELECT
      v2_topic,
      COUNT(*) as total,
      COUNT(DISTINCT v2_part) as parts,
      SUM(CASE WHEN provision_text ~* 'setback|distance.*boundary' THEN 1 ELSE 0 END) as mentions_setback,
      SUM(CASE WHEN provision_text ~* 'not exceed|less than|maximum.*of' THEN 1 ELSE 0 END) as mentions_limits,
      SUM(CASE WHEN provision_text ~* '\\d+\\s*m\\s*2' THEN 1 ELSE 0 END) as has_area_value,
      SUM(CASE WHEN provision_text ~* '\\d+(?:\\.\\d+)?\\s*m(?!2)' THEN 1 ELSE 0 END) as has_height_value
    FROM regulatory_provisions
    WHERE document_id = 'State_Environmental_Planning_Policy_Exempt_and_Complying_Development_Codes_2008__NSW_Legislation'
      AND v2_topic IN ('Deck', 'Fence', 'Pool', 'Carport')
      AND v2_is_actionable = true
    GROUP BY v2_topic
  `);

  console.log('\n=== Structured Data Analysis ===');
  console.log('Topic'.padEnd(12), 'Total', 'Parts', 'Setback', 'Limits', 'Area', 'Height');
  structured.forEach(s => {
    console.log(
      s.v2_topic.padEnd(12),
      s.total.toString().padEnd(5),
      s.parts.toString().padEnd(5),
      s.mentions_setback.toString().padEnd(7),
      s.mentions_limits.toString().padEnd(6),
      s.has_area_value.toString().padEnd(4),
      s.has_height_value.toString().padEnd(6)
    );
  });

  await pool.end();
  process.exit(0);
}

check().catch(err => { console.error(err); process.exit(1); });
