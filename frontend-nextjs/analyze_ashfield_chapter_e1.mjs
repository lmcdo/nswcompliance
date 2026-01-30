import { config } from 'dotenv';
config({ path: '.env.local' });
import pg from 'pg';

const client = new pg.Client({ connectionString: process.env.DATABASE_URL });
await client.connect();

try {
  console.log('=== Ashfield Chapter E1 Deep Analysis ===\n');

  // 1. Check what DCP parts exist in Ashfield condition layer
  const parts = await client.query(`
    SELECT
      v2_dcp_part,
      v2_topic,
      COUNT(*) as count
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
      AND v2_dcp_layer = 'condition'
      AND document_id ILIKE '%Ashfield%'
    GROUP BY v2_dcp_part, v2_topic
    ORDER BY v2_dcp_part, count DESC
  `);

  console.log('## Ashfield Condition Layer - Parts and Topics:');
  let currentPart = '';
  parts.rows.forEach(r => {
    if (r.v2_dcp_part !== currentPart) {
      console.log(`\n### ${r.v2_dcp_part || 'NULL'}:`);
      currentPart = r.v2_dcp_part;
    }
    console.log(`  ${r.v2_topic}: ${r.count}`);
  });

  // 2. Sample the "building_design" provisions in condition layer
  console.log('\n\n## Sample: building_design provisions in Ashfield condition layer');
  console.log('Are these TRULY heritage-specific (e.g., "alterations to heritage items")?');
  console.log('Or are they general provisions that happen to be in Chapter E1?\n');

  const buildingDesign = await client.query(`
    SELECT
      provision_text,
      v2_dcp_part,
      v2_marker,
      v2_heritage_type,
      v2_heritage_element,
      pdf_page
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
      AND v2_dcp_layer = 'condition'
      AND document_id ILIKE '%Ashfield%'
      AND v2_topic = 'building_design'
    ORDER BY pdf_page
    LIMIT 10
  `);

  buildingDesign.rows.forEach((r, i) => {
    console.log(`${i+1}. [${r.v2_dcp_part}] page ${r.pdf_page}`);
    console.log(`   Heritage type: ${r.v2_heritage_type || 'NULL'}`);
    console.log(`   Heritage element: ${r.v2_heritage_element || 'NULL'}`);
    console.log(`   Marker: ${r.v2_marker || 'NULL'}`);
    console.log(`   "${r.provision_text.substring(0, 150)}..."`);
    console.log('');
  });

  // 3. Check if these provisions mention "heritage", "conservation", "HCA" in text
  console.log('\n## Text Analysis: Do non-heritage topics mention heritage?');

  const textAnalysis = await client.query(`
    SELECT
      v2_topic,
      COUNT(*) as total,
      COUNT(*) FILTER (
        WHERE provision_text ILIKE '%heritage%'
           OR provision_text ILIKE '%conservation%'
           OR provision_text ILIKE '%HCA%'
           OR provision_text ILIKE '%listed item%'
      ) as mentions_heritage,
      COUNT(*) FILTER (
        WHERE provision_text NOT ILIKE '%heritage%'
          AND provision_text NOT ILIKE '%conservation%'
          AND provision_text NOT ILIKE '%HCA%'
          AND provision_text NOT ILIKE '%listed item%'
      ) as no_mention
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
      AND v2_dcp_layer = 'condition'
      AND document_id ILIKE '%Ashfield%'
      AND v2_topic != 'heritage'
    GROUP BY v2_topic
    ORDER BY total DESC
  `);

  textAnalysis.rows.forEach(r => {
    const mentionsPct = ((r.mentions_heritage / r.total) * 100).toFixed(0);
    console.log(`  ${r.v2_topic.padEnd(20)} ${r.total.toString().padStart(3)} total | ${r.mentions_heritage.toString().padStart(3)} mention heritage (${mentionsPct}%) | ${r.no_mention.toString().padStart(3)} no mention`);
  });

  // 4. Compare to how Marrickville handles similar provisions
  console.log('\n\n## Comparison: Marrickville Heritage Structure');

  const marrickvilleHeritage = await client.query(`
    SELECT
      v2_dcp_layer,
      v2_topic,
      COUNT(*) as count
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
      AND document_id ILIKE '%Marrickville%'
      AND (v2_topic = 'heritage' OR v2_site_condition_required = 'heritage')
    GROUP BY v2_dcp_layer, v2_topic
    ORDER BY v2_dcp_layer, count DESC
  `);

  console.log('Marrickville heritage provisions by layer:');
  marrickvilleHeritage.rows.forEach(r => {
    console.log(`  ${r.v2_dcp_layer.padEnd(15)} ${r.v2_topic}: ${r.count}`);
  });

  // 5. Check Leichhardt too
  const leichhardtHeritage = await client.query(`
    SELECT
      v2_dcp_layer,
      v2_topic,
      COUNT(*) as count
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
      AND document_id ILIKE '%Leichhardt%'
      AND (v2_topic = 'heritage' OR v2_site_condition_required = 'heritage')
    GROUP BY v2_dcp_layer, v2_topic
    ORDER BY v2_dcp_layer, count DESC
  `);

  console.log('\nLeichhardt heritage provisions by layer:');
  leichhardtHeritage.rows.forEach(r => {
    console.log(`  ${r.v2_dcp_layer.padEnd(15)} ${r.v2_topic}: ${r.count}`);
  });

  console.log('\n\n## Key Questions:');
  console.log('1. Are Ashfield "building_design in Chapter E1" heritage-specific (Option 3)?');
  console.log('2. Or are they general provisions misclassified (Option 2)?');
  console.log('3. How do Marrickville/Leichhardt structure their heritage chapters?');

  // 6. Sample provisions that DON'T mention heritage
  console.log('\n\n## Sample: Provisions with NO heritage mention in text');
  console.log('(These are strongest candidates for reclassification to generic layer)');

  const noMention = await client.query(`
    SELECT
      v2_topic,
      LEFT(provision_text, 150) as text,
      v2_dcp_part,
      pdf_page
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
      AND v2_dcp_layer = 'condition'
      AND document_id ILIKE '%Ashfield%'
      AND v2_topic IN ('building_design', 'fencing', 'trees', 'landscaping', 'access')
      AND provision_text NOT ILIKE '%heritage%'
      AND provision_text NOT ILIKE '%conservation%'
      AND provision_text NOT ILIKE '%HCA%'
      AND provision_text NOT ILIKE '%listed item%'
      AND provision_text NOT ILIKE '%contributory%'
    ORDER BY RANDOM()
    LIMIT 5
  `);

  noMention.rows.forEach((r, i) => {
    console.log(`\n${i+1}. [${r.v2_topic}] ${r.v2_dcp_part} p${r.pdf_page}`);
    console.log(`   "${r.text}..."`);
    console.log(`   ❓ Heritage-specific or generic provision?`);
  });

} finally {
  await client.end();
}
