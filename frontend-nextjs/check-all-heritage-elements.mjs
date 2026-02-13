/**
 * Check ALL heritage elements for provision_text extraction errors
 * Identifies which elements have provisions with wrong text (intro/headers instead of specific controls)
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

console.log('='.repeat(100));
console.log('COMPREHENSIVE HERITAGE ELEMENT TEXT DIAGNOSTIC');
console.log('='.repeat(100));
console.log();

// Get all unique heritage elements
const elementsQuery = await pool.query(`
  SELECT DISTINCT unnest(v2_heritage_element) as element
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
    AND v2_marker = 'heritage'
    AND v2_heritage_element IS NOT NULL
  ORDER BY element
`);

const elements = elementsQuery.rows.map(r => r.element);
console.log(`Found ${elements.length} unique heritage elements:\n${elements.join(', ')}\n`);
console.log('='.repeat(100));
console.log();

// Suspicious patterns indicating WRONG text
const SUSPICIOUS_PATTERNS = [
  /8\.1\.7\s+Heritage Items/i,
  /8\.1\s+General/i,
  /Heritage items are listed in Schedule 5/i,
  /The following controls encourage/i,
  /General controls common to all development/i,
  /Significant internal and external features of heritage ite\./i,
  /^Marrickville Development Control Plan 2011\s+\d+\s+8\./i,  // Just page header + section number
  /^PART 8:\s+HERITAGE\s+\d+/i,  // Just part header
];

const results = [];

// Check each element
for (const element of elements) {
  console.log(`\n${'='.repeat(100)}`);
  console.log(`ELEMENT: ${element.toUpperCase()}`);
  console.log('='.repeat(100));

  const provisions = await pool.query(`
    SELECT
      id,
      pdf_page,
      v2_heritage_type,
      v2_heritage_element,
      LEFT(provision_text, 300) as text_preview
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Marrickville%'
      AND v2_marker = 'heritage'
      AND $1 = ANY(v2_heritage_element)
    ORDER BY pdf_page
    LIMIT 20
  `, [element]);

  let suspicious = 0;
  let looks_ok = 0;
  const issues = [];

  provisions.rows.forEach((p, i) => {
    const text = p.text_preview || '';
    const isSuspicious = SUSPICIOUS_PATTERNS.some(pattern => pattern.test(text));

    // Also check if it contains element-specific keywords
    const hasElementKeyword = new RegExp(element, 'i').test(text);

    if (isSuspicious) {
      suspicious++;
      issues.push({
        id: p.id,
        page: p.pdf_page,
        reason: 'Contains section header/intro text'
      });

      if (i < 3) {  // Show first 3 suspicious ones
        console.log(`\n⚠️  SUSPICIOUS - ID ${p.id} (Page ${p.pdf_page}):`);
        console.log(`   Type: ${p.v2_heritage_type}`);
        console.log(`   Elements: [${p.v2_heritage_element.join(', ')}]`);
        console.log(`   Text: ${text}...`);
      }
    } else if (hasElementKeyword) {
      looks_ok++;

      if (i < 2 && suspicious === 0) {  // Show first good example if no suspicious ones
        console.log(`\n✅ LOOKS OK - ID ${p.id} (Page ${p.pdf_page}):`);
        console.log(`   Contains "${element}" keyword`);
        console.log(`   Text: ${text.substring(0, 150)}...`);
      }
    } else {
      // Unclear - no intro text but also no element keyword
      if (i < 1 && suspicious === 0 && looks_ok === 0) {
        console.log(`\n❓ UNCLEAR - ID ${p.id} (Page ${p.pdf_page}):`);
        console.log(`   No "${element}" keyword found`);
        console.log(`   Text: ${text.substring(0, 150)}...`);
      }
    }
  });

  const total = provisions.rows.length;
  const suspiciousPercent = total > 0 ? ((suspicious / total) * 100).toFixed(1) : 0;

  console.log(`\n${'─'.repeat(100)}`);
  console.log(`SUMMARY for ${element}:`);
  console.log(`  Total provisions: ${total}`);
  console.log(`  Suspicious (wrong): ${suspicious} (${suspiciousPercent}%) ${suspicious > 0 ? '⚠️' : ''}`);
  console.log(`  Looks OK: ${looks_ok} ✅`);
  console.log(`  Unclear: ${total - suspicious - looks_ok}`);

  results.push({
    element,
    total,
    suspicious,
    suspicious_percent: parseFloat(suspiciousPercent),
    looks_ok,
    issues
  });
}

// Overall summary
console.log('\n\n');
console.log('='.repeat(100));
console.log('OVERALL SUMMARY - ALL HERITAGE ELEMENTS');
console.log('='.repeat(100));
console.log();

const totalProvisions = results.reduce((sum, r) => sum + r.total, 0);
const totalSuspicious = results.reduce((sum, r) => sum + r.suspicious, 0);
const totalOK = results.reduce((sum, r) => sum + r.looks_ok, 0);

console.log(`Total provisions checked: ${totalProvisions}`);
console.log(`Total suspicious (wrong text): ${totalSuspicious} (${((totalSuspicious/totalProvisions)*100).toFixed(1)}%) ⚠️`);
console.log(`Total looks OK: ${totalOK} (${((totalOK/totalProvisions)*100).toFixed(1)}%) ✅`);
console.log();

// Rank by severity
const sorted = [...results].sort((a, b) => b.suspicious_percent - a.suspicious_percent);

console.log('ELEMENTS RANKED BY SEVERITY (% with wrong text):');
console.log('-'.repeat(100));
console.table(sorted.map(r => ({
  Element: r.element,
  'Total': r.total,
  'Wrong': r.suspicious,
  '%': r.suspicious_percent + '%',
  'Status': r.suspicious_percent > 50 ? '🔴 CRITICAL' : r.suspicious_percent > 20 ? '🟡 HIGH' : r.suspicious_percent > 0 ? '🟠 MEDIUM' : '✅ OK'
})));

console.log('\nRECOMMENDATION:');
if (totalSuspicious > totalProvisions * 0.1) {
  console.log('🔴 SYSTEMIC ISSUE: >10% of heritage provisions have wrong text.');
  console.log('   This indicates a widespread PDF extraction problem.');
  console.log('   Recommend: Re-run extraction for ALL Marrickville heritage provisions.');
} else if (totalSuspicious > 0) {
  console.log('🟡 ISOLATED ISSUES: Some provisions have wrong text.');
  console.log(`   Elements affected: ${results.filter(r => r.suspicious > 0).map(r => r.element).join(', ')}`);
  console.log('   Recommend: Fix individual provisions or re-extract affected elements.');
} else {
  console.log('✅ NO ISSUES DETECTED: All provisions appear to have correct text.');
}

await pool.end();
