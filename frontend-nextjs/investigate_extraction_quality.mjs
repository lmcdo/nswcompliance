import { config } from 'dotenv';
config({ path: '.env.local' });
import pg from 'pg';

const client = new pg.Client({ connectionString: process.env.DATABASE_URL });
await client.connect();

try {
  console.log('=== Why Did Extraction Process Allow Non-Actionable Text? ===\n');

  // 1. Check extraction metadata
  const metadata = await client.query(`
    SELECT
      v2_provision_type,
      v2_heritage_type,
      COUNT(*) as count,
      AVG(LENGTH(provision_text)) as avg_length
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Ashfield%Chapter_E1%'
      AND v2_is_actionable = true
      AND v2_dcp_layer = 'condition'
    GROUP BY v2_provision_type, v2_heritage_type
    ORDER BY count DESC
  `);

  console.log('## Extraction Types:');
  metadata.rows.forEach(r => {
    console.log(`  ${(r.v2_provision_type || 'NULL').padEnd(15)} ${(r.v2_heritage_type || 'NULL').padEnd(15)} ${r.count.toString().padStart(3)} provisions | avg ${Math.round(r.avg_length)} chars`);
  });

  // 2. Sample "descriptive" provisions marked as actionable
  console.log('\n\n## Sample: v2_heritage_type=descriptive marked as actionable');
  console.log('Question: Should descriptive text ever be v2_is_actionable=true?\n');

  const descriptive = await client.query(`
    SELECT
      v2_provision_type,
      v2_heritage_type,
      LEFT(provision_text, 200) as text,
      LENGTH(provision_text) as len
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Ashfield%Chapter_E1%'
      AND v2_is_actionable = true
      AND v2_heritage_type = 'descriptive'
      AND v2_topic != 'heritage'
    ORDER BY RANDOM()
    LIMIT 8
  `);

  descriptive.rows.forEach((r, i) => {
    console.log(`${i+1}. [${r.v2_provision_type}/${r.v2_heritage_type}] ${r.len} chars`);
    console.log(`   "${r.text}..."`);
    console.log('');
  });

  // 3. Check if there's a pattern - are these from specific PDF sections?
  console.log('\n## PDF Page Distribution: Descriptive vs Control');

  const pageDistribution = await client.query(`
    SELECT
      FLOOR(pdf_page / 20) * 20 as page_range,
      v2_heritage_type,
      COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Ashfield%Chapter_E1%'
      AND v2_is_actionable = true
      AND v2_dcp_layer = 'condition'
    GROUP BY 1, 2
    ORDER BY 1, 2
  `);

  let currentRange = -1;
  pageDistribution.rows.forEach(r => {
    if (r.page_range !== currentRange) {
      console.log(`\nPages ${r.page_range}-${r.page_range + 19}:`);
      currentRange = r.page_range;
    }
    console.log(`  ${(r.v2_heritage_type || 'NULL').padEnd(15)} ${r.count}`);
  });

  // 4. Compare to other councils - do they have descriptive provisions too?
  console.log('\n\n## Comparison: Descriptive Provisions by Council');

  const comparison = await client.query(`
    SELECT
      CASE
        WHEN document_id ILIKE '%Ashfield%' THEN 'Ashfield'
        WHEN document_id ILIKE '%Marrickville%' THEN 'Marrickville'
        WHEN document_id ILIKE '%Leichhardt%' THEN 'Leichhardt'
        ELSE 'Other'
      END as council,
      v2_heritage_type,
      COUNT(*) as count
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
      AND v2_dcp_layer = 'condition'
      AND v2_site_condition_required = 'heritage'
    GROUP BY 1, 2
    ORDER BY 1, 2
  `);

  let currentCouncil2 = '';
  comparison.rows.forEach(r => {
    if (r.council !== currentCouncil2) {
      console.log(`\n${r.council}:`);
      currentCouncil2 = r.council;
    }
    console.log(`  ${(r.v2_heritage_type || 'NULL').padEnd(15)} ${r.count}`);
  });

  // 5. Key insight: Check v2_provision_type distribution
  console.log('\n\n## v2_provision_type Distribution (Ashfield condition layer)');

  const provTypes = await client.query(`
    SELECT
      v2_provision_type,
      v2_topic,
      COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Ashfield%Chapter_E1%'
      AND v2_is_actionable = true
      AND v2_dcp_layer = 'condition'
      AND v2_topic != 'heritage'
    GROUP BY v2_provision_type, v2_topic
    ORDER BY count DESC
  `);

  provTypes.rows.forEach(r => {
    console.log(`  ${(r.v2_provision_type || 'NULL').padEnd(15)} ${r.v2_topic.padEnd(20)} ${r.count}`);
  });

  console.log('\n\n## ROOT CAUSE:');
  console.log('1. Extraction process tagged provisions with v2_heritage_type (control/descriptive)');
  console.log('2. BUT marked ALL as v2_is_actionable=true (no filtering on heritage_type)');
  console.log('3. Descriptive provisions SHOULD NOT be actionable');
  console.log('4. Ashfield Chapter E1 has more descriptive text than Marrickville/Leichhardt');

} finally {
  await client.end();
}
