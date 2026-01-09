import pg from 'pg';
const { Pool } = pg;
const pool = new Pool({connectionString: process.env.DATABASE_URL});

async function checkStructure() {
  try {
    // Get all distinct DCP parts in Marrickville
    const parts = await pool.query(`
      SELECT DISTINCT v2_dcp_part, COUNT(*) as provision_count
      FROM regulatory_provisions
      WHERE document_id ILIKE '%Marrickville%'
      AND v2_dcp_part IS NOT NULL
      AND v2_dcp_part != ''
      GROUP BY v2_dcp_part
      ORDER BY v2_dcp_part
    `);
    
    console.log('=== Marrickville DCP Structure (Distinct Parts) ===');
    console.log('Total distinct parts:', parts.rowCount);
    console.log('');
    
    parts.rows.forEach((r, i) => {
      console.log('[' + (i+1) + '] ' + r.v2_dcp_part + ' (' + r.provision_count + ' provisions)');
    });
    
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await pool.end();
  }
}

checkStructure();
