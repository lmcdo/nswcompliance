import pg from 'pg';
const { Pool } = pg;
const pool = new Pool({connectionString: process.env.DATABASE_URL});

async function searchParkingRates() {
  try {
    // Search for provisions with specific parking numbers
    const rates = await pool.query(`
      SELECT document_id, ref_number, provision_text, pdf_page
      FROM regulatory_provisions
      WHERE document_id ILIKE '%Housing%2021%'
      AND (
        provision_text ~* '0\.2.*parking.*space'
        OR provision_text ~* '0\.4.*parking.*space'
        OR provision_text ~* '0\.5.*parking.*space'
        OR provision_text ~* '1.*parking.*space.*dwelling'
      )
      ORDER BY document_id, id
      LIMIT 30
    `);
    
    console.log('=== Provisions with Parking Rates ===');
    console.log('Total found:', rates.rowCount);
    console.log('');
    
    rates.rows.forEach((r, i) => {
      console.log('[' + (i+1) + '] ' + r.document_id.replace('State_Environmental_Planning_Policy_(Housing)_2021__NSW_Legislation', 'SEPP_H2021'));
      console.log('Ref: ' + (r.ref_number || 'N/A') + ' | Page: ' + (r.pdf_page || 'N/A'));
      console.log(r.provision_text.substring(0, 400));
      console.log('\n---\n');
    });
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await pool.end();
  }
}

searchParkingRates();
