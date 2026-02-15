// Test with ACTUAL PDF table components to find the issue
import { pdf } from '@react-pdf/renderer';
import { createElement } from 'react';
import React from 'react';
import { Page, Text, View, Document, StyleSheet } from '@react-pdf/renderer';

const response = await fetch('http://localhost:3003/api/provisions/for-property?groupBy=toc&former_council=Marrickville&zone=R2&heritage=true&hca=Llewellyn+Estate+Heritage+Conservation+Area&precinct_id=15_');
const data = await response.json();

const allProvisions = [];
if (data.success && data.data.by_layer) {
  for (const layer of data.data.by_layer) {
    allProvisions.push(...layer.provisions);
  }
}

const numericProvisions = allProvisions.filter(p => {
  const text = p.provision_text || '';
  const hasNumeric = /\d+(\.\d+)?\s*(m²|m|mm|cm|km|%|metres?|meters?|centimetres?|centimeters?)/i.test(text);
  const isObjective = /^O\d+|objective|principle|aim/i.test(text);
  return hasNumeric && !isObjective;
});

console.log(`Testing ${numericProvisions.length} provisions with TABLE layout...\n`);

// Replicate the ACTUAL styles from styles.ts (without borders)
const styles = StyleSheet.create({
  page: {
    padding: '10mm 12mm',
    fontSize: 9,
    lineHeight: 1.3,
  },
  tableHeader: {
    flexDirection: 'row',
    backgroundColor: '#f3f4f6',
    padding: 6,
    fontWeight: 'bold',
    fontSize: 8,
  },
  tableRow: {
    flexDirection: 'row',
    padding: 6,
    minHeight: 25,
  },
  colNumber: { width: 30, paddingRight: 5 },
  colSubtopic: { width: 80, paddingRight: 5 },
  colProvision: { flex: 1, paddingRight: 5 },
  colSource: { width: 70 },
  cellProvision: {
    fontSize: 8,
    color: '#1f2937',
    lineHeight: 1.4,
  },
});

function sanitizeText(text) {
  if (!text) return '';
  return text.replace(/-?\d+\.?\d*e[+-]?\d+/gi, '[num]');
}

function truncateText(text) {
  const words = sanitizeText(text).trim().split(/\s+/);
  if (words.length <= 100) return sanitizeText(text);
  return words.slice(0, 100).join(' ') + '...';
}

// Test with TABLE structure (like ProvisionTable.tsx)
async function testWithTableLayout(provisions, startIdx = 0, count = null) {
  const subset = count ? provisions.slice(startIdx, startIdx + count) : provisions.slice(startIdx);

  try {
    const doc = createElement(Document, {},
      createElement(Page, { size: 'A4', style: styles.page },
        // Table header
        createElement(View, { style: styles.tableHeader },
          createElement(Text, { style: styles.colNumber }, '#'),
          createElement(Text, { style: styles.colSubtopic }, 'Subtopic'),
          createElement(Text, { style: styles.colProvision }, 'Provision'),
          createElement(Text, { style: styles.colSource }, 'Source')
        ),
        // Table rows
        ...subset.map((p, idx) =>
          createElement(View, { key: idx, style: styles.tableRow, wrap: false },
            createElement(Text, { style: styles.colNumber }, String(idx + 1)),
            createElement(Text, { style: styles.colSubtopic }, p.v2_topic || '—'),
            createElement(Text, { style: [styles.cellProvision, styles.colProvision] },
              truncateText(p.provision_text || '')
            ),
            createElement(Text, { style: styles.colSource }, `p.${p.pdf_printed_page || p.pdf_page || 1}`)
          )
        )
      )
    );

    await pdf(doc).toBlob();
    console.log(`✓ Table layout [${startIdx}-${startIdx + subset.length - 1}]: SUCCESS`);
    return true;
  } catch (error) {
    console.log(`✗ Table layout [${startIdx}-${startIdx + subset.length - 1}]: FAILED`);
    console.log(`   Error: ${error.message}`);
    return false;
  }
}

// Binary search with table layout
async function bisectTable(provisions, start = 0, label = '') {
  if (provisions.length === 0) return [];

  if (provisions.length === 1) {
    const success = await testWithTableLayout([provisions[0]], start);
    if (!success) {
      console.log(`\n🎯 FOUND: ID ${provisions[0].id} breaks table layout`);
      return [provisions[0]];
    }
    return [];
  }

  const allSuccess = await testWithTableLayout(provisions, start);
  if (allSuccess) return [];

  const mid = Math.floor(provisions.length / 2);
  console.log(`Splitting [${start}-${start + provisions.length - 1}] at position ${start + mid}`);

  const leftProblems = await bisectTable(provisions.slice(0, mid), start);
  const rightProblems = await bisectTable(provisions.slice(mid), start + mid);

  return [...leftProblems, ...rightProblems];
}

const problematic = await bisectTable(numericProvisions);

console.log('\n=== RESULTS ===');
if (problematic.length === 0) {
  console.log('All provisions work with table layout!');
} else {
  console.log(`Found ${problematic.length} provision(s) that break table layout:\n`);
  problematic.forEach(p => {
    console.log(`ID ${p.id}:`);
    console.log(`  Pages: ${p.pdf_page} / ${p.pdf_printed_page}`);
    console.log(`  Length: ${p.provision_text?.length || 0} chars`);
    console.log(`  Text: ${p.provision_text?.substring(0, 200)}...`);
    console.log('');
  });
}
