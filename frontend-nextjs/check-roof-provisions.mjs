/**
 * Diagnostic: Check Roof heritage provision text for extraction errors
 * Uses same DB connection as Next.js app
 */

import pg from 'pg';
const { Pool } = pg;

// Database connection using env vars
const pool = new Pool({
  host: process.env.PGHOST || 'localhost',
  database: process.env.PGDATABASE || 'nsw_planning',
  user: process.env.PGUSER || 'postgres',
  password: process.env.PGPASSWORD,
  port: parseInt(process.env.PGPORT || '5432'),
  ssl: process.env.PGHOST?.includes('supabase') ? { rejectUnauthorized: false } : undefined,
});

console.log('=' * 100);
console.log('DIAGNOSTIC: Roof Heritage Provision Text Check');
console.log('=' + '='.repeat(99));
console.log();

try {
  // Query all Roof heritage provisions for Marrickville
  const query = `
    SELECT
      id,
      pdf_page,
      v2_heritage_type,
      v2_is_actionable,
      section_header,
      LENGTH(provision_text) as text_length,
      provision_text
    FROM regulatory_provisions
    WHERE
      document_id ILIKE '%Marrickville%'
      AND v2_marker = 'heritage'
      AND v2_topic = 'Roof'
    ORDER BY pdf_page, id
  `;

  const result = await pool.query(query);
  const provisions = result.rows;

  console.log(`Found ${provisions.length} Roof heritage provisions in Marrickville DCP`);
  console.log();

  // Patterns that suggest WRONG text
  const SUSPICIOUS_PATTERNS = [
    /8\.1\.7\s+Heritage Items/i,
    /Heritage items are listed in Schedule 5/i,
    /The following controls encourage/i,
    /1\.7\.1\s+General controls common to all development/i,
    /Significant internal and external features of heritage ite\./i,
  ];

  // Patterns that suggest CORRECT text
  const CORRECT_PATTERNS = [
    /8\.1\.7\.[3-9]/,  // Subsection numbers
    /roof|solar|ridgeline|tiles|sheeting|metal|terracotta/i,
  ];

  let suspicious_count = 0;
  let correct_count = 0;
  const issues = [];

  provisions.forEach((p, i) => {
    const text = p.provision_text || '';

    // Check for suspicious patterns
    const is_suspicious = SUSPICIOUS_PATTERNS.some(pattern => pattern.test(text));

    // Check for correct patterns
    const has_roof_content = CORRECT_PATTERNS.some(pattern => pattern.test(text));

    console.log('='.repeat(100));
    console.log(`PROVISION #${i + 1}: ID ${p.id}`);
    console.log('='.repeat(100));
    console.log(`Number:      ${p.id || 'NULL'}`);
    console.log(`Page:        ${p.pdf_page || 'NULL'}`);
    console.log(`Type:        ${p.v2_heritage_type || 'NULL'}`);
    console.log(`Actionable:  ${p.v2_is_actionable}`);
    console.log(`Header:      ${p.section_header || 'NULL'}`);
    console.log(`Length:      ${p.text_length} chars`);
    console.log();

    // Show first 500 chars
    const preview = text.substring(0, 500);
    console.log(`TEXT PREVIEW (${text.length} chars total):`);
    console.log('-'.repeat(100));
    console.log(preview);
    if (text.length > 500) {
      console.log('...');
    }
    console.log('-'.repeat(100));
    console.log();

    // Analysis
    if (is_suspicious) {
      console.log('⚠️  SUSPICIOUS: Contains section intro/header text (likely WRONG)');
      suspicious_count++;
      issues.push({
        id: p.id,
        page: p.pdf_page,
        number: p.id,
        reason: 'Contains intro/header text instead of roof-specific control'
      });
    } else if (has_roof_content) {
      console.log('✅ LOOKS CORRECT: Contains roof-specific content');
      correct_count++;
    } else {
      console.log('❓ UNCLEAR: No obvious roof-specific content, but no intro text either');
      issues.push({
        id: p.id,
        page: p.pdf_page,
        number: p.id,
        reason: 'Missing roof-specific keywords'
      });
    }
    console.log();
  });

  // Summary
  console.log('='.repeat(100));
  console.log('SUMMARY');
  console.log('='.repeat(100));
  console.log(`Total provisions:     ${provisions.length}`);
  console.log(`Suspicious (wrong):   ${suspicious_count} ⚠️`);
  console.log(`Looks correct:        ${correct_count} ✅`);
  console.log(`Unclear:              ${provisions.length - suspicious_count - correct_count} ❓`);
  console.log();

  if (issues.length > 0) {
    console.log(`\n${issues.length} PROVISIONS NEED ATTENTION:`);
    console.log('-'.repeat(100));
    issues.forEach(issue => {
      console.log(`  ID ${String(issue.id).padEnd(6)} | Page ${String(issue.page || 'NULL').padEnd(3)} | ${String(issue.number || 'NULL').padEnd(20)} | ${issue.reason}`);
    });
    console.log();
    console.log('RECOMMENDATION:');
    console.log('These provisions likely have incorrect provision_text extracted from PDF.');
    console.log('They need to be re-extracted with the correct text for roof-specific controls.');
  } else {
    console.log('✅ All provisions look correct!');
  }

} catch (error) {
  console.error('Error:', error.message);
  console.error(error);
} finally {
  await pool.end();
}
