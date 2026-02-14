const { Pool } = require('./frontend-nextjs/node_modules/pg');
require('./frontend-nextjs/node_modules/dotenv').config({ path: './frontend-nextjs/.env.local' });

(async () => {
  const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false }
  });

  console.log('Verifying page number alignment:\n');

  // Get sample provisions with their page numbers
  const { rows } = await pool.query(`
    SELECT id, pdf_page, pdf_printed_page,
           LEFT(provision_text, 100) as text_sample
    FROM regulatory_provisions
    WHERE document_id = 'State_Environmental_Planning_Policy_Exempt_and_Complying_Development_Codes_2008__NSW_Legislation'
      AND v2_topic = 'Deck' AND v2_is_actionable = true
    ORDER BY pdf_page
    LIMIT 5
  `);

  console.log('Sample Deck provisions from database:');
  console.log('ID      | pdf_page | Text Sample');
  console.log('--------|----------|--------------------------------------------------');

  rows.forEach(r => {
    const page = r.pdf_printed_page || r.pdf_page;
    console.log(`${r.id.toString().padEnd(7)} | ${page.toString().padEnd(8)} | ${r.text_sample}...`);
  });

  console.log('\nTo verify alignment:');
  console.log('1. Note the page number above (e.g., page 128)');
  console.log('2. Open: http://localhost:3003/pdf-pages/sepp-exempt-complying/page_128.png');
  console.log('3. Check if the PDF image shows the provision text from the table');
  console.log('\nOr open the image file directly:');
  console.log('   pdf-pages/sepp-exempt-complying/page_128.png');

  await pool.end();
})();
