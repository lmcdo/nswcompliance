import pg from 'pg';
const { Pool } = pg;

const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

async function check() {
  const client = await pool.connect();

  console.log('=== CHECKING C-NUMBER CONTEXT ===\n');

  // Get provisions with C-numbers and extract context around them
  const cProvisions = await client.query(`
    SELECT
      id,
      v2_heritage_type,
      provision_text
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

  cProvisions.rows.forEach((r, i) => {
    const text = r.provision_text;

    // Find C7, C30, C84
    const matches = text.match(/C\d{1,3}/g);
    if (matches) {
      console.log(`\n${i+1}. ID: ${r.id} - Type: ${r.v2_heritage_type}`);

      matches.forEach(match => {
        const index = text.indexOf(match);
        const before = text.substring(Math.max(0, index - 20), index);
        const after = text.substring(index + match.length, Math.min(text.length, index + match.length + 100));

        // Show character codes after C-number
        const afterCodes = after.substring(0, 10).split('').map((c, i) => {
          const code = c.charCodeAt(0);
          let display = c;
          if (code === 10) display = '\\n';
          else if (code === 13) display = '\\r';
          else if (code === 9) display = '\\t';
          else if (code === 32) display = 'SPACE';
          return `[${i}:${code}=${display}]`;
        }).join(' ');

        console.log(`\n   Found: "${match}"`);
        console.log(`   Before: "...${before}"`);
        console.log(`   After codes: ${afterCodes}`);
        console.log(`   After text: "${after.substring(0, 60)}"`);
      });
    }
  });

  // Test if newline BEFORE C-number works
  console.log('\n\n=== TESTING NEWLINE BEFORE C-NUMBER ===\n');

  const nlTest = await client.query(`
    SELECT COUNT(*) as count
    FROM regulatory_provisions
    WHERE v2_marker = 'heritage'
      AND v2_topic = 'Roof'
      AND document_id ILIKE '%Marrickville%'
      AND provision_text ~ '\\nC\\d{1,3}\\s'
  `);
  console.log(`Pattern: \\nC\\d{1,3}\\s (newline before, whitespace after)`);
  console.log(`Matches: ${nlTest.rows[0].count}`);

  // Test simpler pattern
  const simpleTest = await client.query(`
    SELECT COUNT(*) as count
    FROM regulatory_provisions
    WHERE v2_marker = 'heritage'
      AND v2_topic = 'Roof'
      AND document_id ILIKE '%Marrickville%'
      AND provision_text ~ 'C\\d{1,3}'
  `);
  console.log(`\nPattern: C\\d{1,3} (just C-number, no context)`);
  console.log(`Matches: ${simpleTest.rows[0].count}`);

  client.release();
  await pool.end();
}

check().catch(console.error);
