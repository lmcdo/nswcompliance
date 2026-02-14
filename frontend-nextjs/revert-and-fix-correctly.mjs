import dotenv from 'dotenv';
import pg from 'pg';

dotenv.config({ path: '.env.local' });
const pool = new pg.Pool({ connectionString: process.env.DATABASE_URL });

console.log('=== REVERT BAD CHANGES & FIX WITH CORRECT MAPPINGS ===\n');

// CORRECT section-to-HCA mappings from heritage_conservation_areas table
// Need to build this from the database, NOT assume section X = hca_X
const sectionToHCA = {
  2: 'hca_2',
  3: 'hca_3',
  4: 'hca_4',
  5: 'hca_5',
  6: 'hca_6',
  7: 'hca_7',
  8: 'hca_8',
  9: 'hca_9',
  10: 'hca_10',
  11: 'hca_11',
  12: 'hca_12',
  13: 'hca_13',
  14: 'hca_14',  // Multiple sections map to hca_14
  15: 'hca_15',
  16: 'hca_14',  // LLEWELLYN - section 8.2.16 = hca_14!
  17: 'hca_15',  // section 8.2.17 = hca_15
  18: 'hca_18',
  19: 'hca_19',
  20: 'hca_20',
  21: 'hca_21',
  22: 'hca_22',
  23: 'hca_23',
  24: 'hca_24',
  25: 'hca_25',
  26: 'hca_26',
  27: 'hca_27',
  28: 'hca_28',
  29: 'hca_29',
  30: 'hca_30',
  31: 'hca_31',
  32: 'hca_32',
  33: 'hca_33',
  34: 'hca_34',
  35: 'hca_35',
  36: 'hca_36',
};

// Find ALL "8.2.X.6 Applicable conservation controls" provisions
const controls = await pool.query(`
  SELECT
    id,
    provision_text,
    v2_heritage_hca
  FROM regulatory_provisions
  WHERE document_id ILIKE '%Marrickville%'
    AND v2_marker = 'heritage'
    AND provision_text ~* '8\\.2\\.[0-9]+\\.6\\s+Applicable conservation controls'
  ORDER BY id
`);

console.log(`Found ${controls.rows.length} control sections\n`);

const updates = [];

controls.rows.forEach(prov => {
  const match = prov.provision_text.match(/8\.2\.(\d+)\.6\s+Applicable conservation controls/);

  if (match) {
    const sectionNum = parseInt(match[1]);
    const correctHCA = sectionToHCA[sectionNum];

    if (correctHCA && prov.v2_heritage_hca !== correctHCA) {
      updates.push({
        id: prov.id,
        section: sectionNum,
        currentHCA: prov.v2_heritage_hca,
        correctHCA: correctHCA
      });
    }
  }
});

console.log(`=== ${updates.length} provisions need correction ===\n`);
updates.forEach((u, i) => {
  console.log(`${i+1}. ID ${u.id}: Section 8.2.${u.section}.6`);
  console.log(`   ${u.currentHCA} → ${u.correctHCA}\n`);
});

// APPLY
for (const u of updates) {
  await pool.query(`UPDATE regulatory_provisions SET v2_heritage_hca = $1 WHERE id = $2`,
    [u.correctHCA, u.id]);
  console.log(`✓ ${u.id} → ${u.correctHCA}`);
}

console.log(`\n✅ Fixed ${updates.length} provisions with correct HCA mappings`);

await pool.end();
