import { config } from 'dotenv';
import { createClient } from '@supabase/supabase-js';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load environment variables
config({ path: path.join(__dirname, '.env.local') });

const client = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
);

async function examinePrecinctPatterns() {
  console.log('=== EXAMINING PRECINCT PROVISION PATTERNS ===\n');

  // Get sample precinct provisions from each council
  const { data: marrickville, error: mError } = await client
    .from('regulatory_provisions')
    .select('id, document_id, v2_dcp_part, v2_dcp_section, v2_precinct_id')
    .ilike('document_id', '%Marrickville%')
    .eq('v2_dcp_layer', 'precinct')
    .eq('v2_is_actionable', true)
    .limit(10);

  const { data: leichhardt, error: lError } = await client
    .from('regulatory_provisions')
    .select('id, document_id, v2_dcp_part, v2_dcp_section, v2_precinct_id')
    .ilike('document_id', '%Leichhardt%')
    .eq('v2_dcp_layer', 'precinct')
    .eq('v2_is_actionable', true)
    .limit(10);

  const { data: ashfield, error: aError } = await client
    .from('regulatory_provisions')
    .select('id, document_id, v2_dcp_part, v2_dcp_section, v2_precinct_id')
    .ilike('document_id', '%Ashfield%')
    .eq('v2_dcp_layer', 'precinct')
    .eq('v2_is_actionable', true)
    .limit(10);

  if (mError || lError || aError) {
    console.error('Query errors:', { mError, lError, aError });
    return;
  }

  console.log('=== MARRICKVILLE PRECINCT PATTERNS ===');
  console.log(`Found ${marrickville?.length || 0} samples`);
  marrickville?.forEach(p => {
    console.log(`\nDocument: ${p.document_id}`);
    console.log(`Part: ${p.v2_dcp_part}`);
    console.log(`Section: ${p.v2_dcp_section}`);
    console.log(`Current v2_precinct_id: ${p.v2_precinct_id}`);
  });

  console.log('\n\n=== LEICHHARDT PRECINCT PATTERNS ===');
  console.log(`Found ${leichhardt?.length || 0} samples`);
  leichhardt?.forEach(p => {
    console.log(`\nDocument: ${p.document_id}`);
    console.log(`Part: ${p.v2_dcp_part}`);
    console.log(`Section: ${p.v2_dcp_section}`);
    console.log(`Current v2_precinct_id: ${p.v2_precinct_id}`);
  });

  console.log('\n\n=== ASHFIELD PRECINCT PATTERNS ===');
  console.log(`Found ${ashfield?.length || 0} samples`);
  ashfield?.forEach(p => {
    console.log(`\nDocument: ${p.document_id}`);
    console.log(`Part: ${p.v2_dcp_part}`);
    console.log(`Section: ${p.v2_dcp_section}`);
    console.log(`Current v2_precinct_id: ${p.v2_precinct_id}`);
  });

  // Get counts by council
  console.log('\n\n=== PRECINCT PROVISION COUNTS ===');
  const { data: counts } = await client.rpc('get_precinct_counts', {});

  // Manual count queries
  const { count: mCount } = await client
    .from('regulatory_provisions')
    .select('*', { count: 'exact', head: true })
    .ilike('document_id', '%Marrickville%')
    .eq('v2_dcp_layer', 'precinct')
    .eq('v2_is_actionable', true);

  const { count: lCount } = await client
    .from('regulatory_provisions')
    .select('*', { count: 'exact', head: true })
    .ilike('document_id', '%Leichhardt%')
    .eq('v2_dcp_layer', 'precinct')
    .eq('v2_is_actionable', true);

  const { count: aCount } = await client
    .from('regulatory_provisions')
    .select('*', { count: 'exact', head: true })
    .ilike('document_id', '%Ashfield%')
    .eq('v2_dcp_layer', 'precinct')
    .eq('v2_is_actionable', true);

  console.log(`Marrickville: ${mCount} provisions`);
  console.log(`Leichhardt: ${lCount} provisions`);
  console.log(`Ashfield: ${aCount} provisions`);
  console.log(`TOTAL: ${(mCount || 0) + (lCount || 0) + (aCount || 0)} provisions`);

  // Get unique document_ids to understand pattern variety
  console.log('\n\n=== UNIQUE MARRICKVILLE PRECINCT DOCUMENTS ===');
  const { data: mDocs } = await client
    .from('regulatory_provisions')
    .select('document_id')
    .ilike('document_id', '%Marrickville%')
    .eq('v2_dcp_layer', 'precinct')
    .eq('v2_is_actionable', true);

  const uniqueMarrickvilleDocs = [...new Set(mDocs?.map(d => d.document_id) || [])];
  console.log(`Found ${uniqueMarrickvilleDocs.length} unique documents`);
  uniqueMarrickvilleDocs.slice(0, 15).forEach(doc => console.log(`  - ${doc}`));
  if (uniqueMarrickvilleDocs.length > 15) {
    console.log(`  ... and ${uniqueMarrickvilleDocs.length - 15} more`);
  }
}

examinePrecinctPatterns().catch(console.error);
