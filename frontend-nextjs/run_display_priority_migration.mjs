import { config } from 'dotenv';
config({ path: '.env.local' });
import pg from 'pg';
import fs from 'fs';

const client = new pg.Client({ connectionString: process.env.DATABASE_URL });
await client.connect();

try {
  console.log('=== Display Priority Migration ===\n');

  // Check if column exists
  const columnCheck = await client.query(`
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = 'regulatory_provisions'
      AND column_name = 'v2_display_priority'
  `);

  if (columnCheck.rows.length > 0) {
    console.log('⚠️  Column v2_display_priority already exists');
  } else {
    console.log('Adding v2_display_priority column...');
    await client.query(`
      ALTER TABLE regulatory_provisions
      ADD COLUMN v2_display_priority VARCHAR(20)
    `);
    console.log('✅ Column added');
  }

  // Populate display priority
  console.log('\nPopulating display priority based on provision metadata...');

  const update = await client.query(`
    UPDATE regulatory_provisions
    SET v2_display_priority = CASE
      WHEN v2_provision_type = 'control'
       AND v2_has_numeric_value = true
       THEN 'critical'

      WHEN v2_provision_type = 'control'
       AND (v2_has_numeric_value = false OR v2_has_numeric_value IS NULL)
       THEN 'important'

      WHEN v2_provision_type IN ('objective', 'performance_criteria')
       THEN 'guideline'

      WHEN v2_provision_type IN ('note', 'reference')
       THEN 'contextual'

      ELSE 'important'
    END
    WHERE v2_is_actionable = true
      AND (v2_display_priority IS NULL OR v2_display_priority != CASE
        WHEN v2_provision_type = 'control'
         AND v2_has_numeric_value = true
         THEN 'critical'
        WHEN v2_provision_type = 'control'
         AND (v2_has_numeric_value = false OR v2_has_numeric_value IS NULL)
         THEN 'important'
        WHEN v2_provision_type IN ('objective', 'performance_criteria')
         THEN 'guideline'
        WHEN v2_provision_type IN ('note', 'reference')
         THEN 'contextual'
        ELSE 'important'
      END)
  `);

  console.log(`✅ Updated ${update.rowCount} provisions`);

  // Create index
  console.log('\nCreating index for fast filtering...');

  await client.query(`
    CREATE INDEX IF NOT EXISTS idx_provisions_display_priority
    ON regulatory_provisions(v2_display_priority)
    WHERE v2_is_actionable = true
  `);

  console.log('✅ Index created');

  // Verification
  console.log('\n\n## Distribution by Priority Level');
  console.log('─'.repeat(70));

  const distribution = await client.query(`
    SELECT
      v2_display_priority,
      COUNT(*) as total,
      COUNT(*) FILTER (WHERE document_id ILIKE '%Ashfield%') as ashfield,
      COUNT(*) FILTER (WHERE document_id ILIKE '%Marrickville%') as marrickville,
      COUNT(*) FILTER (WHERE document_id ILIKE '%Leichhardt%') as leichhardt
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
    GROUP BY v2_display_priority
    ORDER BY
      CASE v2_display_priority
        WHEN 'critical' THEN 1
        WHEN 'important' THEN 2
        WHEN 'guideline' THEN 3
        WHEN 'contextual' THEN 4
        ELSE 5
      END
  `);

  console.log('\nPriority      Total    Ashfield  Marrickville  Leichhardt');
  distribution.rows.forEach(r => {
    console.log(
      `${(r.v2_display_priority || 'NULL').padEnd(12)} ${r.total.toString().padStart(6)} ${r.ashfield.toString().padStart(10)} ${r.marrickville.toString().padStart(13)} ${r.leichhardt.toString().padStart(11)}`
    );
  });

  // Sample provisions by priority
  console.log('\n\n## Sample Provisions by Priority');
  console.log('─'.repeat(70));

  for (const priority of ['critical', 'important', 'guideline']) {
    const samples = await client.query(`
      SELECT
        LEFT(provision_text, 100) as text,
        v2_topic,
        v2_provision_type,
        v2_has_numeric_value
      FROM regulatory_provisions
      WHERE v2_is_actionable = true
        AND v2_display_priority = $1
      ORDER BY RANDOM()
      LIMIT 3
    `, [priority]);

    console.log(`\n### ${priority.toUpperCase()}`);
    samples.rows.forEach((r, i) => {
      console.log(`${i+1}. [${r.v2_topic}] ${r.v2_provision_type}${r.v2_has_numeric_value ? ' (numeric)' : ''}`);
      console.log(`   "${r.text}..."`);
    });
  }

  console.log('\n\n✅ Migration complete!');
  console.log('   Provisions ranked by display priority for progressive disclosure');

} finally {
  await client.end();
}
