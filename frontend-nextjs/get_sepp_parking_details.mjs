import pg from 'pg';
const { Pool } = pg;
const pool = new Pool({connectionString: process.env.DATABASE_URL});

async function getSEPPParkingDetails() {
  try {
    // Get complete provisions for key parking sections
    
    console.log('=== SECTION 19: In-Fill Affordable Housing ===\n');
    const s19 = await pool.query(`
      SELECT ref_number, provision_text, pdf_page
      FROM regulatory_provisions
      WHERE document_id ILIKE '%Housing%2021%section_19%'
      AND (provision_text ILIKE '%parking%' OR provision_text ILIKE '%accessible%area%')
      ORDER BY id
      LIMIT 10
    `);
    s19.rows.forEach(r => {
      console.log('Ref: ' + (r.ref_number || 'N/A') + ' | Page: ' + (r.pdf_page || 'N/A'));
      console.log(r.provision_text);
      console.log('\n---\n');
    });
    
    console.log('\n=== SECTION 24: Boarding Houses ===\n');
    const s24 = await pool.query(`
      SELECT ref_number, provision_text, pdf_page
      FROM regulatory_provisions
      WHERE document_id ILIKE '%Housing%2021%section_24%'
      AND provision_text ILIKE '%parking%'
      ORDER BY id
      LIMIT 10
    `);
    s24.rows.forEach(r => {
      console.log('Ref: ' + (r.ref_number || 'N/A') + ' | Page: ' + (r.pdf_page || 'N/A'));
      console.log(r.provision_text);
      console.log('\n---\n');
    });
    
    console.log('\n=== SECTION 74: Build-to-Rent ===\n');
    const s74 = await pool.query(`
      SELECT ref_number, provision_text, pdf_page
      FROM regulatory_provisions
      WHERE document_id ILIKE '%Housing%2021%section_27%'
      AND (provision_text ILIKE '%parking%' OR ref_number ILIKE '%74%')
      ORDER BY id
      LIMIT 10
    `);
    s74.rows.forEach(r => {
      console.log('Ref: ' + (r.ref_number || 'N/A') + ' | Page: ' + (r.pdf_page || 'N/A'));
      console.log(r.provision_text);
      console.log('\n---\n');
    });
    
    console.log('\n=== SECTION 157: TOD Affordable Housing ===\n');
    const s157 = await pool.query(`
      SELECT ref_number, provision_text, pdf_page
      FROM regulatory_provisions
      WHERE document_id ILIKE '%Housing%2021%'
      AND (ref_number ILIKE '%157%' OR provision_text ILIKE '%157%')
      ORDER BY id
      LIMIT 15
    `);
    s157.rows.forEach(r => {
      console.log('Ref: ' + (r.ref_number || 'N/A') + ' | Page: ' + (r.pdf_page || 'N/A'));
      console.log(r.provision_text);
      console.log('\n---\n');
    });
    
    console.log('\n=== Accessible Area Definition ===\n');
    const accessible = await pool.query(`
      SELECT provision_text, pdf_page
      FROM regulatory_provisions
      WHERE document_id ILIKE '%Housing%2021%'
      AND provision_text ILIKE '%accessible area%means%'
      LIMIT 5
    `);
    accessible.rows.forEach(r => {
      console.log('Page: ' + (r.pdf_page || 'N/A'));
      console.log(r.provision_text);
      console.log('\n---\n');
    });
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await pool.end();
  }
}

getSEPPParkingDetails();
