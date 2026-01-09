const { createClient } = require('@supabase/supabase-js');
require('dotenv').config({ path: '.env.local' });

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

(async () => {
  console.log('=== HONEST SEPP DATA AUDIT ===\n');

  const { data: seppData } = await supabase
    .from('sepp_structured_requirements')
    .select('sepp_id, section_name');

  console.log('1. sepp_structured_requirements:');
  if (!seppData || seppData.length === 0) {
    console.log('   ❌ EMPTY');
  } else {
    const counts = {};
    seppData.forEach(r => counts[r.sepp_id] = (counts[r.sepp_id] || 0) + 1);
    for (const [id, count] of Object.entries(counts)) {
      console.log('   ✅ ' + id + ': ' + count);
    }
  }

  const { data: adgData } = await supabase
    .from('sepp_adg_requirements')
    .select('criteria_id');

  console.log('\n2. sepp_adg_requirements:');
  console.log('   ' + (adgData?.length > 0 ? '✅' : '❌') + ' ' + (adgData?.length || 0) + ' ADG criteria');

  console.log('\n3. Claimed vs Reality:');
  const claimed = ['housing_2021', 'sustainable_buildings_2022', 'resilience_hazards_2021', 'transport_infrastructure_2021', 'biodiversity_conservation_2017'];

  for (const id of claimed) {
    const has = seppData?.some(r => r.sepp_id === id) || (id === 'housing_2021' && adgData?.length > 0);
    console.log('   ' + (has ? '✅' : '❌ FAKE') + '  ' + id);
  }

  console.log('\n=== VERDICT ===');
  console.log('Real data: sustainable_buildings_2022, housing_2021 ADG');
  console.log('Fake: resilience_hazards, transport, biodiversity (badges only)');
})();
