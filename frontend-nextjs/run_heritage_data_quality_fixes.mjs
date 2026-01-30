import { config } from 'dotenv';
config({ path: '.env.local' });
import pg from 'pg';

const client = new pg.Client({ connectionString: process.env.DATABASE_URL });
await client.connect();

try {
  console.log('=== Heritage Data Quality Fixes ===\n');
  console.log('Fixing extraction quality issues where descriptive text marked as actionable\n');

  // Fix 1: Mark descriptive provisions as non-actionable
  console.log('## Fix 1: Descriptive Provisions');
  console.log('─'.repeat(70));

  const preview1 = await client.query(`
    SELECT COUNT(*) as count
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
      AND v2_dcp_layer = 'condition'
      AND v2_site_condition_required = 'heritage'
      AND v2_heritage_type = 'descriptive'
  `);

  console.log(`Provisions to update: ${preview1.rows[0].count}`);

  const fix1 = await client.query(`
    UPDATE regulatory_provisions
    SET v2_is_actionable = false
    WHERE v2_is_actionable = true
      AND v2_dcp_layer = 'condition'
      AND v2_site_condition_required = 'heritage'
      AND v2_heritage_type = 'descriptive'
    RETURNING document_id
  `);

  console.log(`✅ Updated ${fix1.rowCount} provisions (descriptive → non-actionable)`);

  // Fix 2: Mark character statements that are pure descriptions
  console.log('\n\n## Fix 2: Character Statements (Pure Descriptions)');
  console.log('─'.repeat(70));

  const preview2 = await client.query(`
    SELECT COUNT(*) as count
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
      AND v2_dcp_layer = 'condition'
      AND v2_site_condition_required = 'heritage'
      AND v2_heritage_type = 'character'
      AND v2_provision_type != 'control'
  `);

  console.log(`Provisions to update: ${preview2.rows[0].count}`);

  const fix2 = await client.query(`
    UPDATE regulatory_provisions
    SET v2_is_actionable = false
    WHERE v2_is_actionable = true
      AND v2_dcp_layer = 'condition'
      AND v2_site_condition_required = 'heritage'
      AND v2_heritage_type = 'character'
      AND v2_provision_type != 'control'
    RETURNING document_id
  `);

  console.log(`✅ Updated ${fix2.rowCount} provisions (character descriptions → non-actionable)`);

  // Fix 3: Mark definitions as non-actionable
  console.log('\n\n## Fix 3: Definitions');
  console.log('─'.repeat(70));

  const preview3 = await client.query(`
    SELECT COUNT(*) as count
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
      AND v2_dcp_layer = 'condition'
      AND v2_site_condition_required = 'heritage'
      AND v2_provision_type = 'definition'
  `);

  console.log(`Provisions to update: ${preview3.rows[0].count}`);

  const fix3 = await client.query(`
    UPDATE regulatory_provisions
    SET v2_is_actionable = false
    WHERE v2_is_actionable = true
      AND v2_dcp_layer = 'condition'
      AND v2_site_condition_required = 'heritage'
      AND v2_provision_type = 'definition'
    RETURNING document_id
  `);

  console.log(`✅ Updated ${fix3.rowCount} provisions (definitions → non-actionable)`);

  // Summary
  console.log('\n\n## Summary');
  console.log('─'.repeat(70));

  const summary = await client.query(`
    SELECT
      CASE
        WHEN document_id ILIKE '%Ashfield%' THEN 'Ashfield'
        WHEN document_id ILIKE '%Marrickville%' THEN 'Marrickville'
        WHEN document_id ILIKE '%Leichhardt%' THEN 'Leichhardt'
        ELSE 'Other'
      END as council,
      v2_is_actionable,
      COUNT(*) as count
    FROM regulatory_provisions
    WHERE v2_dcp_layer = 'condition'
      AND v2_site_condition_required = 'heritage'
    GROUP BY 1, 2
    ORDER BY 1, 2 DESC
  `);

  console.log('\nHeritage condition provisions by council:');
  let currentCouncil = '';
  summary.rows.forEach(r => {
    if (r.council !== currentCouncil) {
      console.log(`\n${r.council}:`);
      currentCouncil = r.council;
    }
    const label = r.v2_is_actionable ? 'Actionable' : 'Non-actionable';
    console.log(`  ${label.padEnd(15)} ${r.count}`);
  });

  // Impact analysis
  console.log('\n\n## Impact Analysis');
  console.log('─'.repeat(70));

  console.log('\nBefore fixes:');
  console.log('  Ashfield heritage property:     907 provisions');
  console.log('  Marrickville heritage property: 208 provisions');

  const ashfieldAfter = await client.query(`
    SELECT COUNT(*) as count
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
      AND v2_dcp_layer = 'condition'
      AND v2_site_condition_required = 'heritage'
      AND document_id ILIKE '%Ashfield%'
  `);

  const marrickvilleAfter = await client.query(`
    SELECT COUNT(*) as count
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
      AND v2_dcp_layer = 'condition'
      AND v2_site_condition_required = 'heritage'
      AND document_id ILIKE '%Marrickville%'
  `);

  console.log('\nAfter fixes:');
  console.log(`  Ashfield heritage property:     ${ashfieldAfter.rows[0].count} provisions (${907 - ashfieldAfter.rows[0].count} removed)`);
  console.log(`  Marrickville heritage property: ${marrickvilleAfter.rows[0].count} provisions (${208 - marrickvilleAfter.rows[0].count} removed)`);

  console.log('\n✅ Data quality fixes complete!');
  console.log('   Heritage properties now show only actionable controls');
  console.log('   Descriptive text, character statements, and definitions excluded');

} finally {
  await client.end();
}
