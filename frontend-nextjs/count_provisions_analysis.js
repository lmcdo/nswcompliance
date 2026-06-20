const { Pool } = require('pg');
const pool = new Pool({
  host: 'aws-1-ap-southeast-2.pooler.supabase.com',
  port: 6543,
  database: 'postgres',
  user: 'postgres.llzdrxywpziewrzudwhj',
  password: process.env.PGPASSWORD,
  ssl: { rejectUnauthorized: false }
});

async function analyzeProvisions() {
  try {
    // Total count
    const total = await pool.query('SELECT COUNT(*) as count FROM regulatory_provisions');
    console.log('TOTAL PROVISIONS:', total.rows[0].count);
    console.log('');

    // By document type
    const byType = await pool.query(`
      SELECT document_type, COUNT(*) as count
      FROM regulatory_provisions
      GROUP BY document_type
      ORDER BY count DESC
    `);
    console.log('BY DOCUMENT TYPE:');
    byType.rows.forEach(row => {
      console.log(`  ${row.document_type || 'null'}: ${Number(row.count).toLocaleString()}`);
    });
    console.log('');

    // By provision type
    const byProvType = await pool.query(`
      SELECT provision_type, COUNT(*) as count
      FROM regulatory_provisions
      GROUP BY provision_type
      ORDER BY count DESC
    `);
    console.log('BY PROVISION TYPE:');
    byProvType.rows.forEach(row => {
      console.log(`  ${row.provision_type || 'null'}: ${Number(row.count).toLocaleString()}`);
    });
    console.log('');

    // By council (inferred from document_id)
    const byCouncil = await pool.query(`
      SELECT
        CASE
          WHEN document_id ILIKE '%Ashfield%' THEN 'Ashfield'
          WHEN document_id ILIKE '%Marrickville%' THEN 'Marrickville'
          WHEN document_id ILIKE '%Leichhardt%' THEN 'Leichhardt'
          WHEN document_id ILIKE '%SEPP%' THEN 'SEPP'
          ELSE 'Other'
        END as council,
        COUNT(*) as count
      FROM regulatory_provisions
      GROUP BY 1
      ORDER BY count DESC
    `);
    console.log('BY COUNCIL:');
    byCouncil.rows.forEach(row => {
      console.log(`  ${row.council}: ${Number(row.count).toLocaleString()}`);
    });
    console.log('');

    // Top 25 documents by provision count
    const byDoc = await pool.query(`
      SELECT document_id, COUNT(*) as count
      FROM regulatory_provisions
      GROUP BY document_id
      ORDER BY count DESC
      LIMIT 25
    `);
    console.log('TOP 25 DOCUMENTS BY PROVISION COUNT:');
    byDoc.rows.forEach(row => {
      console.log(`  ${row.document_id}: ${Number(row.count).toLocaleString()}`);
    });
    console.log('');

    // Actionable vs non-actionable
    const actionable = await pool.query(`
      SELECT
        v2_is_actionable,
        COUNT(*) as count
      FROM regulatory_provisions
      GROUP BY v2_is_actionable
      ORDER BY v2_is_actionable DESC NULLS LAST
    `);
    console.log('ACTIONABLE STATUS:');
    actionable.rows.forEach(row => {
      const status = row.v2_is_actionable === true ? 'Actionable' :
                     row.v2_is_actionable === false ? 'Not Actionable' : 'null';
      console.log(`  ${status}: ${Number(row.count).toLocaleString()}`);
    });

  } catch (error) {
    console.error('Error:', error);
  } finally {
    await pool.end();
  }
}

analyzeProvisions();
