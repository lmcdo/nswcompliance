// Bisect to find which provision breaks PDF rendering
import { pdf } from '@react-pdf/renderer';
import { createElement } from 'react';
import React from 'react';
import { Page, Text, View, Document, StyleSheet } from '@react-pdf/renderer';

const response = await fetch('http://localhost:3003/api/provisions/for-property?groupBy=toc&former_council=Marrickville&zone=R2&heritage=true&hca=Llewellyn+Estate+Heritage+Conservation+Area&precinct_id=15_');
const data = await response.json();

// Extract all provisions
const allProvisions = [];
if (data.success && data.data.by_layer) {
  for (const layer of data.data.by_layer) {
    allProvisions.push(...layer.provisions);
  }
}

// Filter for numeric provisions (same logic as component)
const numericProvisions = allProvisions.filter(p => {
  const text = p.provision_text || '';
  const hasNumeric = /\d+(\.\d+)?\s*(m²|m|mm|cm|km|%|metres?|meters?|centimetres?|centimeters?)/i.test(text);
  const isObjective = /^O\d+|objective|principle|aim/i.test(text);
  return hasNumeric && !isObjective;
});

console.log(`Testing ${numericProvisions.length} numeric provisions by binary search...\n`);

// Simple PDF styles
const styles = StyleSheet.create({
  page: { padding: 20 },
  text: { fontSize: 9, marginBottom: 5 }
});

// Sanitize text (remove scientific notation)
function sanitizeText(text) {
  if (!text) return '';
  return text.replace(/-?\d+\.?\d*e[+-]?\d+/gi, '[num]');
}

// Truncate to 100 words
function truncateText(text) {
  const words = text.trim().split(/\s+/);
  if (words.length <= 100) return text;
  return words.slice(0, 100).join(' ') + '...';
}

// Sanitize page numbers
function sanitizePage(val) {
  if (!val || val < 0 || val > 1000) return 1;
  return Math.round(val);
}

// Test if a set of provisions can render
async function testProvisions(provisions, label) {
  try {
    const doc = createElement(Document, {},
      createElement(Page, { size: 'A4', style: styles.page },
        ...provisions.map((p, idx) =>
          createElement(Text, { key: idx, style: styles.text },
            `${p.id}: ${truncateText(sanitizeText(p.provision_text || '')).substring(0, 150)}`
          )
        )
      )
    );

    await pdf(doc).toBlob();
    console.log(`✓ ${label}: SUCCESS (${provisions.length} provisions)`);
    return true;
  } catch (error) {
    console.log(`✗ ${label}: FAILED - ${error.message.substring(0, 100)}`);
    return false;
  }
}

// Binary search to find problematic provision(s)
async function bisect(provisions, start = 0) {
  if (provisions.length === 0) {
    console.log('No provisions to test');
    return [];
  }

  if (provisions.length === 1) {
    const success = await testProvisions(provisions, `Single provision ${provisions[0].id}`);
    if (!success) {
      console.log(`\n🎯 FOUND PROBLEMATIC PROVISION: ID ${provisions[0].id}`);
      console.log(`   pdf_page: ${provisions[0].pdf_page}`);
      console.log(`   pdf_printed_page: ${provisions[0].pdf_printed_page}`);
      console.log(`   text length: ${provisions[0].provision_text?.length || 0}`);
      console.log(`   preview: ${provisions[0].provision_text?.substring(0, 200)}...`);
      return [provisions[0]];
    }
    return [];
  }

  // Test all provisions
  const allSuccess = await testProvisions(provisions, `All ${provisions.length} provisions (${start}-${start + provisions.length - 1})`);
  if (allSuccess) {
    console.log('All provisions render successfully!');
    return [];
  }

  // Split in half
  const mid = Math.floor(provisions.length / 2);
  const left = provisions.slice(0, mid);
  const right = provisions.slice(mid);

  console.log(`\nSplitting into: [${start}-${start + mid - 1}] and [${start + mid}-${start + provisions.length - 1}]`);

  const leftProblems = await bisect(left, start);
  const rightProblems = await bisect(right, start + mid);

  return [...leftProblems, ...rightProblems];
}

// Run bisection
const problematic = await bisect(numericProvisions);

console.log('\n\n=== SUMMARY ===');
if (problematic.length === 0) {
  console.log('No problematic provisions found!');
} else {
  console.log(`Found ${problematic.length} problematic provision(s):`);
  problematic.forEach(p => {
    console.log(`\nID ${p.id}:`);
    console.log(`  pdf_page: ${p.pdf_page}, pdf_printed_page: ${p.pdf_printed_page}`);
    console.log(`  text length: ${p.provision_text?.length || 0} chars`);
    console.log(`  v2_marker: ${p.v2_marker}`);
    console.log(`  v2_topic: ${p.v2_topic}`);
    console.log(`  preview: ${p.provision_text?.substring(0, 300)}...`);
  });
}
