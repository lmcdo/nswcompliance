import pg from 'pg';
const { Pool } = pg;

const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

const r2BaseUrl = 'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev';

async function updateR2Urls() {
  try {
    const updateQuery = `
      UPDATE sepp_structured_requirements
      SET requirement_data = jsonb_set(
        requirement_data,
        '{pdf_references}',
        $1::jsonb
      )
      WHERE sepp_id = 'resilience_hazards_2021' AND section = '4.6'
      RETURNING id
    `;
    
    const pdfRefs = [
      {
        page: 20,
        section: "4.6",
        description: "Contamination consideration requirements",
        image_url: `${r2BaseUrl}/pdf-pages/sepp-resilience-hazards/page-20.png`
      },
      {
        page: 21,
        section: "4.6(4)",
        description: "When preliminary investigation required - trigger conditions",
        image_url: `${r2BaseUrl}/pdf-pages/sepp-resilience-hazards/page-21.png`
      },
      {
        page: 25,
        section: "4.8",
        description: "Category 1 remediation work requiring consent",
        image_url: `${r2BaseUrl}/pdf-pages/sepp-resilience-hazards/page-25.png`
      }
    ];
    
    const result = await pool.query(updateQuery, [JSON.stringify(pdfRefs)]);
    console.log('[UPDATE] Rows updated:', result.rowCount);
    
    // Verify
    const verify = await pool.query(`
      SELECT 
        sepp_id, section,
        requirement_data->'pdf_references'->0->>'image_url' as url1,
        requirement_data->'pdf_references'->1->>'image_url' as url2,
        requirement_data->'pdf_references'->2->>'image_url' as url3
      FROM sepp_structured_requirements
      WHERE sepp_id = 'resilience_hazards_2021' AND section = '4.6'
    `);
    
    console.log('\n[VERIFICATION] R2 URLs in database:');
    const row = verify.rows[0];
    console.log('  Page 20:', row.url1);
    console.log('  Page 21:', row.url2);
    console.log('  Page 25:', row.url3);
    
  } catch (error) {
    console.error('[ERROR]', error.message);
  } finally {
    await pool.end();
  }
}

updateR2Urls();
