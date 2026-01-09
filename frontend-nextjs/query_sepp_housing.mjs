import pg from 'pg';
const { Pool } = pg;
const pool = new Pool({connectionString: process.env.DATABASE_URL});

async function querySEPPHousing() {
  try {
    // Get all SEPP Housing sections
    const sections = await pool.query(`
      SELECT DISTINCT document_id, COUNT(*) as provision_count
      FROM regulatory_provisions
      WHERE document_id ILIKE '%Housing%2021%'
      GROUP BY document_id
      ORDER BY document_id
    `);
    
    console.log('=== SEPP Housing 2021 Sections ===');
    console.log('Total sections:', sections.rowCount);
    console.log('');
    
    sections.rows.forEach(r => {
      console.log(r.document_id + ' (' + r.provision_count + ' provisions)');
    });
    
    // Get parking-related provisions
    console.log('\n=== Parking-Related Provisions ===\n');
    
    const parking = await pool.query(`
      SELECT ref_number, section_header, provision_text, pdf_page
      FROM regulatory_provisions
      WHERE document_id ILIKE '%Housing%2021%'
      AND provision_text ILIKE '%parking%'
      ORDER BY document_id, ref_number
      LIMIT 20
    `);
    
    console.log('Total parking provisions:', parking.rowCount);
    console.log('');
    
    parking.rows.forEach((r, i) => {
      console.log('[' + (i+1) + '] Ref: ' + (r.ref_number || 'N/A'));
      console.log('    Section: ' + (r.section_header || 'N/A'));
      console.log('    Page: ' + (r.pdf_page || 'N/A'));
      console.log('    Text: ' + (r.provision_text || '').substring(0, 200) + '...');
      console.log('');
    });
    
    // Get accessible area provisions
    console.log('\n=== Accessible Area Provisions ===\n');
    
    const accessible = await pool.query(`
      SELECT ref_number, section_header, provision_text, pdf_page
      FROM regulatory_provisions
      WHERE document_id ILIKE '%Housing%2021%'
      AND provision_text ILIKE '%accessible%area%'
      LIMIT 15
    `);
    
    console.log('Total accessible area provisions:', accessible.rowCount);
    console.log('');
    
    accessible.rows.forEach((r, i) => {
      console.log('[' + (i+1) + '] Ref: ' + (r.ref_number || 'N/A'));
      console.log('    Section: ' + (r.section_header || 'N/A'));
      console.log('    Page: ' + (r.pdf_page || 'N/A'));
      console.log('    Text: ' + (r.provision_text || '').substring(0, 250) + '...');
      console.log('');
    });
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await pool.end();
  }
}

querySEPPHousing();
