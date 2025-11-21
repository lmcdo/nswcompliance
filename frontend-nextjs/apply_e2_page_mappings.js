const { Pool } = require('pg');
const fs = require('fs');

const envContent = fs.readFileSync('.env.local', 'utf8');
const dbUrl = envContent.split('\n').find(line => line.startsWith('DATABASE_URL=')).split('=')[1].trim();
const pool = new Pool({ connectionString: dbUrl });

const updates = [
  { id: 2329, page: 2, section: 'Existing Character' },
  { id: 2330, page: 3, section: 'Objectives O1' },
  { id: 2331, page: 3, section: 'Objectives O2' },
  { id: 2332, page: 3, section: 'Objectives O3' },
  { id: 2340, page: 3, section: 'Objectives O7' },
  { id: 2336, page: 4, section: 'Controls C1/C5' },
  { id: 2335, page: 3, section: 'Controls C3' },
  { id: 2333, page: 9, section: 'Controls C22' },
  { id: 2334, page: 9, section: 'Controls C22' },
  { id: 2337, page: 6, section: 'Controls C9' },
  { id: 2338, page: 6, section: 'Controls C11' },
  { id: 2339, page: 6, section: 'Controls C12' },
];

async function applyUpdates() {
  console.log('[+] Creating backup...');
  await pool.query(`
    CREATE TABLE IF NOT EXISTS dcp_precinct_requirements_backup_e2_pdf AS
    SELECT * FROM dcp_precinct_requirements WHERE precinct_id = 'E2'
  `);
  console.log('[OK] Backup created');

  console.log('\n[+] Updating E2 requirements with PDF page mappings...\n');

  for (const update of updates) {
    await pool.query(`
      UPDATE dcp_precinct_requirements
      SET
        pdf_pages = ARRAY[$1::integer],
        pdf_page_image_url = $2
      WHERE id = $3
    `, [update.page, `/pdf-pages/leichhardt-e2/page_${update.page}.png`, update.id]);

    console.log(`[OK] ID ${update.id} -> Page ${update.page} (${update.section})`);
  }

  console.log('\n[+] Verifying updates...\n');
  const result = await pool.query(`
    SELECT id, requirement_text, pdf_pages, pdf_page_image_url
    FROM dcp_precinct_requirements
    WHERE precinct_id = 'E2'
    ORDER BY id
  `);

  result.rows.forEach(row => {
    const page = row.pdf_pages ? row.pdf_pages[0] : 'NULL';
    console.log(`ID ${row.id}: Page ${page} - ${row.requirement_text.substring(0, 50)}...`);
  });

  await pool.end();

  console.log('\n[SUCCESS] All E2 requirements updated with PDF pages!');
  console.log('\n[NEXT STEP] Refresh browser and test with 34 Dalhousie St, Haberfield');
}

applyUpdates().catch(err => {
  console.error('Error:', err);
  pool.end();
});
