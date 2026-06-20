import pg from 'pg';
const { Pool } = pg;

const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

async function check() {
  const client = await pool.connect();

  console.log('=== CHECKING C-NUMBER FORMAT ===\n');

  // Get provisions that contain "C7", "C30", "C84" etc.
  const cProvisions = await client.query(`
    SELECT
      id,
      v2_heritage_type,
      LEFT(provision_text, 200) as text,
      LENGTH(provision_text) as text_length
    FROM regulatory_provisions
    WHERE v2_marker = 'heritage'
      AND v2_topic = 'Roof'
      AND document_id ILIKE '%Marrickville%'
      AND (
        provision_text LIKE '%C7 %'
        OR provision_text LIKE '%C30 %'
        OR provision_text LIKE '%C84 %'
      )
    LIMIT 5
  `);

  console.log(`Found ${cProvisions.rows.length} provisions with C-numbers\n`);

  cProvisions.rows.forEach((r, i) => {
    console.log(`\n${i+1}. ID: ${r.id}`);
    console.log(`   Type: ${r.v2_heritage_type}`);
    console.log(`   Length: ${r.text_length} chars`);
    console.log(`   Text: "${r.text}"`);

    // Show first 50 chars in hex to see whitespace
    const hex = r.text.substring(0, 50).split('').map(c => {
      const code = c.charCodeAt(0);
      if (code === 10) return '\\n';
      if (code === 13) return '\\r';
      if (code === 9) return '\\t';
      if (code === 32) return '_';
      return c;
    }).join('');
    console.log(`   Hex: "${hex}"`);
  });

  // Also check what the regex is actually matching
  console.log('\n\n=== TESTING REGEX PATTERNS ===\n');

  const patterns = [
    `provision_text ~ '^\\\\s*C\\\\d{1,3}[\\\\s\\\\n]'`,
    `provision_text ~ 'C\\\\d{1,3}[\\\\s\\\\n]'`,
    `provision_text ~ 'C\\\\d+'`,
    `provision_text LIKE 'C%'`,
  ];

  for (const pattern of patterns) {
    const result = await client.query(`
      SELECT COUNT(*) as count
      FROM regulatory_provisions
      WHERE v2_marker = 'heritage'
        AND v2_topic = 'Roof'
        AND document_id ILIKE '%Marrickville%'
        AND ${pattern}
    `);
    console.log(`Pattern: ${pattern}`);
    console.log(`Matches: ${result.rows[0].count}\n`);
  }

  client.release();
  await pool.end();
}

check().catch(console.error);
