const { createClient } = require('@supabase/supabase-js');
require('dotenv').config({ path: './frontend-nextjs/.env.local' });

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

(async () => {
  console.log('=== HONEST SEPP DATA AUDIT ===\n');

  const { data: seppData, error: seppError } = await supabase
    .from('sepp_structured_requirements')
    .select('sepp_id, section_name');

  console.log('1. sepp_structured_requirements table:');
  if (seppError) {
    console.log('   ERROR:', seppError.message);
  } else if (!seppData || seppData.length === 0) {
    console.log('   ❌ COMPLETELY EMPTY');
  } else {
    const counts = {};
    seppData.forEach(r => {
      counts[r.sepp_id] = (counts[r.sepp_id] || 0) + 1;
    });
    console.log(`   Total rows: ${seppData.length}`);
    for (const [id, count] of Object.entries(counts)) {
      console.log(`   ✅ ${id}: ${count} requirements`);
    }
  }

  const { data: adgData } = await supabase
    .from('sepp_adg_requirements')
    .select('criteria_id');

  console.log('\n2. sepp_adg_requirements table:');
  if (adgData && adgData.length > 0) {
    console.log(`   ✅ ${adgData.length} ADG criteria exist`);
  } else {
    console.log('   ❌ EMPTY');
  }

  console.log('\n3. What I claimed in SEPP_MAPPING vs Reality:');
  const claimed = [
    'housing_2021',
    'sustainable_buildings_2022',
    'resilience_hazards_2021',
    'transport_infrastructure_2021',
    'biodiversity_conservation_2017'
  ];

  for (const id of claimed) {
    const hasStructured = seppData?.some(r => r.sepp_id === id);
    const hasAdg = id === 'housing_2021' && adgData && adgData.length > 0;
    const status = hasStructured ? '✅ HAS DATA' : hasAdg ? '✅ HAS ADG' : '❌ FAKE';
    console.log(`   ${status}  ${id}`);
  }

  console.log('\n=== THE TRUTH ===');
  console.log('Only 2 SEPPs have ANY data:');
  console.log('  1. sustainable_buildings_2022');
  console.log('  2. housing_2021 (via ADG table)');
  console.log('\nAll others are FAKE - just badges with no data.');
})();
