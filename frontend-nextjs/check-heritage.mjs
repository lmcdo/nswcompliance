import pg from 'pg';
const { Pool } = pg;

const pool = new Pool({
  host: process.env.PGHOST || 'localhost',
  database: process.env.PGDATABASE || 'nsw_planning',
  user: process.env.PGUSER || 'postgres',
  password: process.env.PGPASSWORD,
  port: parseInt(process.env.PGPORT || '5432'),
  ssl: process.env.PGHOST?.includes('supabase') ? { rejectUnauthorized: false } : undefined,
});

console.log('=== Checking heritage provisions ===\n');

// Check document IDs containing Marrickville
const docs = await pool.query(`
  SELECT DISTINCT document_id
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
  LIMIT 5
`);
console.log('Sample Marrickville document_ids:');
docs.rows.forEach(r => console.log('  ', r.document_id));
console.log();

// Check heritage markers
const markers = await pool.query(`
  SELECT v2_marker, COUNT(*) as count
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
  GROUP BY v2_marker
  ORDER BY count DESC
  LIMIT 10
`);
console.log('v2_marker values for Marrickville:');
markers.rows.forEach(r => console.log(`   ${(r.v2_marker || 'NULL').padEnd(20)} ${r.count}`));
console.log();

// Check topics for heritage marker
const topics = await pool.query(`
  SELECT v2_topic, COUNT(*) as count
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
    AND v2_marker = 'heritage'
  GROUP BY v2_topic
  ORDER BY count DESC
  LIMIT 20
`);
console.log('v2_topic values for Marrickville heritage provisions:');
topics.rows.forEach(r => console.log(`   ${(r.v2_topic || 'NULL').padEnd(30)} ${r.count}`));
console.log();

// Check if "Roof" topic exists at all
const roof = await pool.query(`
  SELECT COUNT(*) as count
  FROM regulatory_provisions
  WHERE v2_topic ILIKE '%roof%'
`);
console.log(`Total provisions with topic containing "roof": ${roof.rows[0].count}`);

await pool.end();
