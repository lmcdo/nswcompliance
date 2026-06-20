import pg from 'pg';
const { Pool } = pg;

const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

async function check() {
  const client = await pool.connect();

  console.log('=== HERITAGE TOPIC STRUCTURE IN SUPABASE ===\n');

  // Check v2_topic values for Marrickville heritage
  console.log('Marrickville Heritage v2_topic distribution:');
  const topicCheck = await client.query(`
    SELECT v2_topic, v2_marker, COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Marrickville%8.0%Heritage%'
    GROUP BY v2_topic, v2_marker
    ORDER BY count DESC
    LIMIT 20
  `);
  console.table(topicCheck.rows);

  // Check Ashfield Summer Hill HCA for comparison
  console.log('\n\nAshfield Heritage (Summer Hill) v2_topic distribution:');
  const ashfieldCheck = await client.query(`
    SELECT v2_topic, v2_marker, COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Ashfield%'
      AND v2_marker = 'heritage'
    GROUP BY v2_topic, v2_marker
    ORDER BY count DESC
    LIMIT 20
  `);
  console.table(ashfieldCheck.rows);

  client.release();
  await pool.end();
}

check().catch(console.error);
