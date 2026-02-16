#!/usr/bin/env node

/**
 * Find AI-generated commentary contaminating provision text
 * Provisions should contain ONLY actual DCP text, no framing/commentary
 */

import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load environment variables
const result = dotenv.config({ path: path.join(__dirname, '.env.local') });
if (result.error) {
  console.error('❌ Error loading .env.local:', result.error.message);
}

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error('❌ Missing Supabase credentials');
  process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

// AI commentary patterns to search for
const AI_PATTERNS = [
  'key heritage provision text extracted from this page',
  'key provision text extracted',
  'extracted from this page is:',
  'the key provision',
  'provision text extracted',
  'based on the image',
  'from the provided',
  'according to the',
  'the text states',
  'the provision states',
  'this provision indicates',
  'the document specifies',
  'as per the document',
];

async function findAICommentary() {
  console.log('🔍 Searching for AI commentary in provision_text...\n');

  const results = [];

  for (const pattern of AI_PATTERNS) {
    console.log(`Searching for: "${pattern}"...`);

    const { data, error } = await supabase
      .from('regulatory_provisions')
      .select('id, provision_text, v2_dcp_part, v2_topic, pdf_page, former_council')
      .ilike('provision_text', `%${pattern}%`);

    if (error) {
      console.error(`Error searching for "${pattern}":`, error.message);
      continue;
    }

    if (data && data.length > 0) {
      console.log(`  ❌ Found ${data.length} instances!`);
      results.push(...data.map(p => ({ ...p, pattern })));
    } else {
      console.log(`  ✅ No instances found`);
    }
  }

  console.log('\n' + '='.repeat(80));
  console.log(`TOTAL CONTAMINATED PROVISIONS: ${results.length}`);
  console.log('='.repeat(80) + '\n');

  if (results.length > 0) {
    console.log('📋 CONTAMINATED PROVISIONS:\n');

    // Group by pattern
    const byPattern = {};
    results.forEach(r => {
      if (!byPattern[r.pattern]) byPattern[r.pattern] = [];
      byPattern[r.pattern].push(r);
    });

    for (const [pattern, provisions] of Object.entries(byPattern)) {
      console.log(`\n${'─'.repeat(80)}`);
      console.log(`Pattern: "${pattern}" (${provisions.length} provisions)`);
      console.log('─'.repeat(80));

      provisions.slice(0, 5).forEach((p, idx) => {
        console.log(`\n${idx + 1}. ID: ${p.id} | ${p.former_council} | ${p.v2_dcp_part} | ${p.v2_topic} | Page ${p.pdf_page}`);
        console.log(`   Text preview: ${p.provision_text?.substring(0, 200)}...`);
      });

      if (provisions.length > 5) {
        console.log(`\n   ... and ${provisions.length - 5} more`);
      }
    }

    console.log('\n' + '='.repeat(80));
    console.log('💡 RECOMMENDATION:');
    console.log('These provisions need to be cleaned or re-extracted without AI commentary.');
    console.log('The provision_text should contain ONLY the actual DCP text.');
    console.log('='.repeat(80));

    // Export IDs for cleanup
    const contaminatedIds = results.map(r => r.id);
    console.log(`\n📋 Contaminated provision IDs (${contaminatedIds.length} total):`);
    console.log(contaminatedIds.join(', '));
  } else {
    console.log('✅ No AI commentary found! Database is clean.');
  }
}

findAICommentary().catch(console.error);
