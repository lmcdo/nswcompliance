import dotenv from 'dotenv';
import pg from 'pg';

dotenv.config({ path: '.env.local' });

const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });

// Check what the API returns for Marrickville heritage provisions
const total = await pool.query(`
  SELECT COUNT(*) as count
  FROM regulatory_provisions
  WHERE v2_is_actionable = true
    AND v2_marker = 'heritage'
    AND document_id ILIKE '%Marrickville%'
`);
console.log('Total Marrickville actionable heritage provisions:', total.rows[0].count);

// By DCP part
const byPart = await pool.query(`
  SELECT
    v2_dcp_part,
    COUNT(*) as count,
    COUNT(*) FILTER (WHERE v2_heritage_hca IS NULL) as general,
    COUNT(*) FILTER (WHERE v2_heritage_hca IS NOT NULL) as hca_specific
  FROM regulatory_provisions
  WHERE v2_is_actionable = true
    AND v2_marker = 'heritage'
    AND document_id ILIKE '%Marrickville%'
  GROUP BY v2_dcp_part
  ORDER BY v2_dcp_part
`);
console.log('\nBy DCP Part:');
byPart.rows.forEach(r => {
  console.log(`  ${r.v2_dcp_part || 'NULL'}: ${r.count} total (${r.general} general + ${r.hca_specific} HCA-specific)`);
});

// Check Part 8 specifically with topic breakdown
const part8 = await pool.query(`
  SELECT
    v2_topic,
    COUNT(*) as count,
    COUNT(*) FILTER (WHERE v2_heritage_hca IS NULL) as general,
    COUNT(*) FILTER (WHERE v2_heritage_hca IS NOT NULL) as hca_specific
  FROM regulatory_provisions
  WHERE v2_is_actionable = true
    AND v2_marker = 'heritage'
    AND document_id ILIKE '%Marrickville%'
    AND v2_dcp_part = 'Part 8'
  GROUP BY v2_topic
  ORDER BY v2_topic
`);
console.log('\nPart 8 by Topic:');
part8.rows.forEach(r => {
  console.log(`  ${r.v2_topic}: ${r.count} (${r.general} general + ${r.hca_specific} HCA)`);
});

await pool.end();
