/**
 * Test provision formatter with REAL data from database
 * This will help identify what's actually broken in the formatter
 */

import { createClient } from '@supabase/supabase-js';
import { parseProvisionText, stripSectionHeader } from './lib/provision-text-formatter.ts';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://mzgomctrfgkwbowqkpew.supabase.co';
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im16Z29tY3RyZmdrd2Jvd3FrcGV3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzAwMTUxNjAsImV4cCI6MjA0NTU5MTE2MH0.x7xUUKQZ_LlzgwLiTQTv9t-BYM2D0TXDXhzn2p8wpfk';

const supabase = createClient(supabaseUrl, supabaseKey);

async function testRealProvisions() {
  console.log('Fetching real Marrickville DCP provisions from database...\n');

  // Fetch a variety of provisions to test different formats
  const { data: provisions, error } = await supabase
    .from('regulatory_provisions')
    .select('id, provision_text, section_header, toc_section_title, section_number')
    .eq('document_id', 1) // Marrickville DCP
    .in('section_number', [
      '4.1.1', // Objectives
      '4.1.2', // Planning context (has numbered lists)
      '4.1.6.1', // Floor space ratio (has roman numerals)
      '4.1.8', // Dormer windows
      '4.1.9', // Additional controls
    ])
    .order('section_number');

  if (error) {
    console.error('Error fetching provisions:', error);
    return;
  }

  if (!provisions || provisions.length === 0) {
    console.log('No provisions found');
    return;
  }

  console.log(`Found ${provisions.length} provisions\n`);
  console.log('='.repeat(80));

  for (const prov of provisions) {
    console.log(`\nPROVISION ID: ${prov.id}`);
    console.log(`SECTION: ${prov.section_number} - ${prov.section_header || prov.toc_section_title}`);
    console.log('-'.repeat(80));

    console.log('\n📝 RAW TEXT FROM DATABASE:');
    console.log(JSON.stringify(prov.provision_text, null, 2));

    console.log('\n🔧 AFTER stripSectionHeader():');
    const stripped = stripSectionHeader(prov.provision_text, prov.section_header);
    console.log(JSON.stringify(stripped, null, 2));

    console.log('\n🎨 PARSED ELEMENTS:');
    const elements = parseProvisionText(stripped, { skipHeadings: false });
    console.log(JSON.stringify(elements, null, 2));

    console.log('\n📊 ELEMENT SUMMARY:');
    const summary = elements.reduce((acc, el) => {
      acc[el.type] = (acc[el.type] || 0) + 1;
      return acc;
    }, {});
    console.log(summary);

    console.log('\n' + '='.repeat(80));
  }
}

// Run the test
testRealProvisions().catch(console.error);
