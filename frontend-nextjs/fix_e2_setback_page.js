const { Pool } = require('pg');
const fs = require('fs');

const envContent = fs.readFileSync('.env.local', 'utf8');
const dbUrl = envContent.split('\n').find(line => line.startsWith('DATABASE_URL=')).split('=')[1].trim();
const pool = new Pool({ connectionString: dbUrl });

// Fix ID 2333 - should be page 4 (Pattern of Development section), not page 9
pool.query(`
  UPDATE dcp_precinct_requirements
  SET
    pdf_pages = ARRAY[4],
    pdf_page_image_url = '/pdf-pages/leichhardt-e2/page_4.png'
  WHERE id = 2333
`)
.then(() => {
  console.log('[OK] Fixed ID 2333: Moved from page 9 -> page 4 (Pattern of Development)');
  return pool.query(`
    SELECT id, requirement_text, pdf_pages
    FROM dcp_precinct_requirements
    WHERE id IN (2333, 2334)
    ORDER BY id
  `);
})
.then(result => {
  console.log('\nVerification:');
  result.rows.forEach(r => {
    console.log(`  ID ${r.id}: Page ${r.pdf_pages[0]} - ${r.requirement_text.substring(0,50)}...`);
  });
  pool.end();
})
.catch(err => {
  console.error('Error:', err);
  pool.end();
});
