const { Pool } = require('./frontend-nextjs/node_modules/pg');

(async () => {
  const pool = new Pool({
    connectionString: 'postgresql://postgres.llzdrxywpziewrzudwhj:eDDIYq8ottiaO9ll@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres',
    ssl: { rejectUnauthorized: false }
  });

  console.log('Fixing LaTeX math artifacts in provision text...\n');

  // Count provisions with LaTeX artifacts
  const before = await pool.query(`SELECT COUNT(*) FROM regulatory_provisions WHERE provision_text LIKE '%$%\\%%'`);
  console.log(`Provisions with LaTeX math artifacts: ${before.rows[0].count}`);

  // Fix LaTeX percent signs: \% → %
  console.log('\n1. Fixing \\% → %');
  const fix1 = await pool.query(`
    UPDATE regulatory_provisions
    SET provision_text = REPLACE(provision_text, '\\%', '%')
    WHERE provision_text LIKE '%\\%%'
  `);
  console.log(`   ✓ Fixed ${fix1.rowCount} provisions`);

  // Fix LaTeX math delimiters: $number → number (but preserve $ for currency)
  console.log('\n2. Removing LaTeX math delimiters...');
  const fix2 = await pool.query(`
    UPDATE regulatory_provisions
    SET provision_text = regexp_replace(provision_text, '\\$([0-9])', '\\1', 'g')
    WHERE provision_text ~ '\\$[0-9]'
  `);
  console.log(`   ✓ Fixed ${fix2.rowCount} provisions`);

  // Fix more complex LaTeX patterns: $x \mathsf{m}$ → x m
  console.log('\n3. Fixing LaTeX math expressions...');
  const fix3 = await pool.query(`
    UPDATE regulatory_provisions
    SET provision_text = regexp_replace(provision_text, '\\$([^$]+)\\\\mathsf\\{\\s*([^}]+)\\s*\\}\\$', '\\1 \\2', 'g')
    WHERE provision_text LIKE '%\\mathsf%'
  `);
  console.log(`   ✓ Fixed ${fix3.rowCount} provisions`);

  // Fix LaTeX multiplication: \times → ×
  console.log('\n4. Fixing \\times → ×');
  const fix4 = await pool.query(`
    UPDATE regulatory_provisions
    SET provision_text = REPLACE(provision_text, '\\times', '×')
    WHERE provision_text LIKE '%\\times%'
  `);
  console.log(`   ✓ Fixed ${fix4.rowCount} provisions`);

  // Fix LaTeX exponents: $x^{y}$ → x^y or just remove for common cases
  console.log('\n5. Fixing LaTeX exponents...');
  const fix5 = await pool.query(`
    UPDATE regulatory_provisions
    SET provision_text = regexp_replace(provision_text, '\\$([0-9]+)\\s*\\^\\s*\\{\\s*0\\s*\\}\\$', '\\1°', 'g')
    WHERE provision_text ~ '\\$[0-9]+\\s*\\^\\s*\\{\\s*0\\s*\\}\\$'
  `);
  console.log(`   ✓ Fixed ${fix5.rowCount} degree symbols`);

  // Verify and sample
  const after = await pool.query(`SELECT COUNT(*) FROM regulatory_provisions WHERE provision_text LIKE '%$%'`);
  console.log(`\nRemaining provisions with $: ${after.rows[0].count}`);

  // Sample fixed provision
  const sample = await pool.query(`
    SELECT id, LEFT(provision_text, 250) as sample
    FROM regulatory_provisions
    WHERE id = 78392
  `);

  console.log('\nSample (landscaping provision):');
  console.log(`  ${sample.rows[0].sample}...`);

  await pool.end();
  console.log('\n✓ Complete');
})();
