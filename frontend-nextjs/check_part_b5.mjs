import pg from 'pg';
const { Pool } = pg;
const pool = new Pool({connectionString: process.env.DATABASE_URL});

async function checkPartB5() {
  try {
    // Check for Part B5 or B5 references
    const result = await pool.query(`
      SELECT 
        v2_precinct_id,
        v2_dcp_part,
        ref_number,
        section_header,
        provision_text,
        document_id
      FROM regulatory_provisions
      WHERE document_id ILIKE '%Marrickville%'
      AND (
        v2_dcp_part ILIKE '%B5%'
        OR v2_dcp_part ILIKE '%Part B%'
        OR section_header ILIKE '%Part B%'
        OR section_header ILIKE '%B5%'
        OR provision_text ILIKE '%Part B5%'
      )
      LIMIT 20
    `);
    
    console.log('=== "Part B5" or "Part B" References in Marrickville DCP ===');
    console.log('Total found:', result.rowCount);
    console.log('');
    
    if (result.rowCount === 0) {
      console.log('NO PART B5 FOUND - Perplexity likely hallucinated this\n');
    } else {
      result.rows.forEach((r, i) => {
        console.log('[' + (i+1) + '] Precinct: ' + (r.v2_precinct_id || 'N/A'));
        console.log('    DCP Part: ' + (r.v2_dcp_part || 'N/A'));
        console.log('    Ref: ' + (r.ref_number || 'N/A'));
        console.log('    Section: ' + (r.section_header || 'N/A'));
        console.log('    Text: ' + (r.provision_text || '').substring(0, 200) + '...');
        console.log('');
      });
    }
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await pool.end();
  }
}

checkPartB5();
