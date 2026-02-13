/**
 * Check heritage extraction quality across ALL councils
 */

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

const SUSPICIOUS_PATTERNS = [
  /8\.1\.7\s+Heritage Items/i,
  /8\.1\s+General/i,
  /Heritage items are listed in Schedule 5/i,
  /The following controls encourage/i,
  /General controls common to all development/i,
  /^Marrickville Development Control Plan 2011\s+\d+\s+8\./i,
  /^Ashfield Development Control Plan\s+\d+\s+Chapter/i,
  /^Leichhardt Development Control Plan\s+\d+\s+Part/i,
  /^PART 8:\s+HERITAGE\s+\d+/i,
  /^Chapter E1:\s+HERITAGE/i,
];

const councils = ['Marrickville', 'Ashfield', 'Leichhardt'];
const results = [];

for (const council of councils) {
  console.log(`\n${'='.repeat(100)}`);
  console.log(`COUNCIL: ${council.toUpperCase()}`);
  console.log('='.repeat(100));

  // Get total heritage provisions
  const total = await pool.query(`
    SELECT COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id ILIKE $1
      AND v2_marker = 'heritage'
  `, [`%${council}%`]);

  const totalCount = parseInt(total.rows[0].count);
  console.log(`Total heritage provisions: ${totalCount}`);

  if (totalCount === 0) {
    console.log('⚠️  NO HERITAGE PROVISIONS FOUND\n');
    results.push({ council, total: 0, suspicious: 0, percent: 0 });
    continue;
  }

  // Sample 50 random provisions to check quality
  const sample = await pool.query(`
    SELECT
      id,
      pdf_page,
      v2_heritage_element,
      v2_heritage_type,
      LEFT(provision_text, 300) as text_preview
    FROM regulatory_provisions
    WHERE document_id ILIKE $1
      AND v2_marker = 'heritage'
    ORDER BY RANDOM()
    LIMIT 50
  `, [`%${council}%`]);

  let suspicious = 0;
  const issues = [];

  sample.rows.forEach(p => {
    const text = p.text_preview || '';
    const isSuspicious = SUSPICIOUS_PATTERNS.some(pattern => pattern.test(text));

    if (isSuspicious) {
      suspicious++;
      issues.push(p.id);
    }
  });

  const suspiciousPercent = ((suspicious / sample.rows.length) * 100).toFixed(1);
  const estimatedBadTotal = Math.round((suspicious / sample.rows.length) * totalCount);

  console.log(`Sample size: ${sample.rows.length}`);
  console.log(`Suspicious in sample: ${suspicious} (${suspiciousPercent}%)`);
  console.log(`Estimated bad provisions: ~${estimatedBadTotal} out of ${totalCount}`);

  if (suspicious > 0) {
    console.log(`\nExample bad provision IDs: ${issues.slice(0, 5).join(', ')}`);
  }

  const status = suspiciousPercent > 50 ? '🔴 CRITICAL' : suspiciousPercent > 20 ? '🟡 HIGH' : suspiciousPercent > 0 ? '🟠 MEDIUM' : '✅ OK';
  console.log(`Status: ${status}`);

  results.push({
    council,
    total: totalCount,
    sample: sample.rows.length,
    suspicious,
    percent: parseFloat(suspiciousPercent),
    estimated_bad: estimatedBadTotal
  });
}

console.log('\n\n');
console.log('='.repeat(100));
console.log('CROSS-COUNCIL SUMMARY');
console.log('='.repeat(100));
console.table(results.map(r => ({
  Council: r.council,
  'Total Provisions': r.total,
  'Sample Size': r.sample,
  'Bad in Sample': r.suspicious,
  '% Bad': r.percent + '%',
  'Est. Total Bad': r.estimated_bad,
  Status: r.percent > 50 ? '🔴' : r.percent > 20 ? '🟡' : r.percent > 0 ? '🟠' : '✅'
})));

const totalProvisions = results.reduce((sum, r) => sum + r.total, 0);
const totalEstimatedBad = results.reduce((sum, r) => sum + r.estimated_bad, 0);

console.log(`\nOVERALL: ~${totalEstimatedBad} bad provisions out of ${totalProvisions} total (${((totalEstimatedBad/totalProvisions)*100).toFixed(1)}%)`);

if (totalEstimatedBad > 0) {
  console.log('\n🔴 RECOMMENDATION: Re-extract ALL heritage provisions across all councils.');
  console.log('The extraction logic was fundamentally flawed.');
}

await pool.end();
