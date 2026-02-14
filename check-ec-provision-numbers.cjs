const { Pool } = require('./frontend-nextjs/node_modules/pg');
require('./frontend-nextjs/node_modules/dotenv').config({ path: './frontend-nextjs/.env.local' });

(async () => {
  const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false }
  });

  // First check available columns
  const { rows: cols } = await pool.query(`
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = 'regulatory_provisions'
    ORDER BY ordinal_position
  `);

  console.log('Available columns:');
  console.log(cols.map(c => c.column_name).join(', '));
  console.log('\n');

  // Now get sample data
  const { rows } = await pool.query(`
    SELECT id, pdf_page, pdf_printed_page,
           LEFT(provision_text, 100) as text_preview
    FROM regulatory_provisions
    WHERE document_id = 'State_Environmental_Planning_Policy_Exempt_and_Complying_Development_Codes_2008__NSW_Legislation'
      AND v2_topic = 'Deck' AND v2_is_actionable = true
    LIMIT 3
  `);

  console.log('Deck Provisions - Sample Data:');
  rows.forEach(r => {
    console.log(`\nID: ${r.id}`);
    console.log(`Pages: pdf_page=${r.pdf_page}, pdf_printed_page=${r.pdf_printed_page}`);
    console.log(`Text: ${r.text_preview}...`);
  });

  await pool.end();
})();
