import dotenv from 'dotenv';
import pg from 'pg';
const { Pool } = pg;
dotenv.config({ path: '.env.local' });

const pool = new Pool({
  host: process.env.PGHOST,
  database: process.env.PGDATABASE,
  user: process.env.PGUSER,
  password: process.env.PGPASSWORD,
  port: parseInt(process.env.PGPORT || '5432'),
  ssl: process.env.PGHOST?.includes('supabase') ? { rejectUnauthorized: false } : undefined,
});

// Check text lengths to see if they look truncated
const result = await pool.query(`
  SELECT id, LENGTH(provision_text) as len, RIGHT(provision_text, 10) as ending
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
    AND v2_marker = 'heritage'
  ORDER BY len DESC
  LIMIT 20
`);

console.log('Longest provisions (checking for truncation):');
result.rows.forEach(r => {
  console.log(`  ID ${r.id}: ${r.len} chars, ends with: "${r.ending}"`);
});

// Count how many end with "..."
const truncated = await pool.query(`
  SELECT COUNT(*) as count
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
    AND v2_marker = 'heritage'
    AND provision_text LIKE '%...'
`);
console.log(`\nProvisions ending with "...": ${truncated.rows[0].count}`);

// Check length distribution
const dist = await pool.query(`
  SELECT 
    CASE
      WHEN LENGTH(provision_text) < 100 THEN '<100'
      WHEN LENGTH(provision_text) BETWEEN 100 AND 299 THEN '100-299'
      WHEN LENGTH(provision_text) BETWEEN 300 AND 310 THEN '300-310 (LIKELY TRUNCATED)'
      WHEN LENGTH(provision_text) > 310 THEN '>310'
    END as range,
    COUNT(*) as count
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
    AND v2_marker = 'heritage'
  GROUP BY 1
  ORDER BY 1
`);
console.log('\nLength distribution:');
dist.rows.forEach(r => console.log(`  ${r.range}: ${r.count}`));

await pool.end();
