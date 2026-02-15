// Systematic test: Start with working code, add complexity until it breaks
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
}).slice(0, 163); // Exactly 163 like the actual export

console.log(`Testing with ${numericProvisions.length} provisions\n`);

const styles = StyleSheet.create({
  page: { padding: '10mm 12mm', fontSize: 9 },
  tableRow: { flexDirection: 'row', padding: 6, minHeight: 25 },
  col1: { width: 30 },
  col2: { width: 80 },
  col3: { flex: 1 },
  col4: { width: 70 },
  footer: {
    position: 'absolute',
    bottom: 10,
    left: 12,
    right: 12,
    fontSize: 7,
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
});

function sanitize(text) {
  return (text || '').replace(/-?\d+\.?\d*e[+-]?\d+/gi, '[num]');
}

function truncate(text) {
  const words = sanitize(text).trim().split(/\s+/);
  return words.length <= 100 ? sanitize(text) : words.slice(0, 100).join(' ') + '...';
}

// Test 1: Basic table (KNOWN TO WORK)
async function test1() {
  console.log('Test 1: Basic table, no footer...');
  try {
    const doc = createElement(Document, {},
      createElement(Page, { size: 'A4', style: styles.page },
        ...numericProvisions.map((p, i) =>
          createElement(View, { key: i, style: styles.tableRow },
            createElement(Text, { style: styles.col1 }, String(i + 1)),
            createElement(Text, { style: styles.col3 }, truncate(p.provision_text || ''))
          )
        )
      )
    );
    await pdf(doc).toBlob();
    console.log('✓ Test 1 PASSED\n');
    return true;
  } catch (e) {
    console.log(`✗ Test 1 FAILED: ${e.message}\n`);
    return false;
  }
}

// Test 2: Add fixed footer
async function test2() {
  console.log('Test 2: Add fixed footer...');
  try {
    const doc = createElement(Document, {},
      createElement(Page, { size: 'A4', style: styles.page },
        ...numericProvisions.map((p, i) =>
          createElement(View, { key: i, style: styles.tableRow },
            createElement(Text, { style: styles.col1 }, String(i + 1)),
            createElement(Text, { style: styles.col3 }, truncate(p.provision_text || ''))
          )
        ),
        createElement(View, { style: styles.footer, fixed: true },
          createElement(Text, {}, 'Footer'),
          createElement(Text, {}, 'Page')
        )
      )
    );
    await pdf(doc).toBlob();
    console.log('✓ Test 2 PASSED\n');
    return true;
  } catch (e) {
    console.log(`✗ Test 2 FAILED: ${e.message}\n`);
    return false;
  }
}

// Test 3: Add page numbers in footer
async function test3() {
  console.log('Test 3: Add render callback for page numbers...');
  try {
    const doc = createElement(Document, {},
      createElement(Page, { size: 'A4', style: styles.page },
        ...numericProvisions.map((p, i) =>
          createElement(View, { key: i, style: styles.tableRow },
            createElement(Text, { style: styles.col1 }, String(i + 1)),
            createElement(Text, { style: styles.col3 }, truncate(p.provision_text || ''))
          )
        ),
        createElement(View, { style: styles.footer, fixed: true },
          createElement(Text, {}, 'Footer'),
          createElement(Text, { render: ({ pageNumber, totalPages }) => `${pageNumber} / ${totalPages}` }, '')
        )
      )
    );
    await pdf(doc).toBlob();
    console.log('✓ Test 3 PASSED\n');
    return true;
  } catch (e) {
    console.log(`✗ Test 3 FAILED: ${e.message}\n`);
    return false;
  }
}

// Test 4: Add page numbers from provision data
async function test4() {
  console.log('Test 4: Show pdf_printed_page in source column...');
  try {
    const doc = createElement(Document, {},
      createElement(Page, { size: 'A4', style: styles.page },
        ...numericProvisions.map((p, i) =>
          createElement(View, { key: i, style: styles.tableRow },
            createElement(Text, { style: styles.col1 }, String(i + 1)),
            createElement(Text, { style: styles.col3 }, truncate(p.provision_text || '')),
            createElement(Text, { style: styles.col4 }, `p.${p.pdf_printed_page || p.pdf_page || 1}`)
          )
        )
      )
    );
    await pdf(doc).toBlob();
    console.log('✓ Test 4 PASSED\n');
    return true;
  } catch (e) {
    console.log(`✗ Test 4 FAILED: ${e.message}\n`);
    console.log(`Error details: ${e.stack}\n`);
    return false;
  }
}

// Test 5: Multiple pages (Cover + Provisions)
async function test5() {
  console.log('Test 5: Add cover page...');
  try {
    const doc = createElement(Document, {},
      createElement(Page, { size: 'A4', style: styles.page },
        createElement(Text, { style: { fontSize: 20 } }, 'COVER PAGE')
      ),
      createElement(Page, { size: 'A4', style: styles.page },
        ...numericProvisions.map((p, i) =>
          createElement(View, { key: i, style: styles.tableRow },
            createElement(Text, { style: styles.col1 }, String(i + 1)),
            createElement(Text, { style: styles.col3 }, truncate(p.provision_text || ''))
          )
        )
      )
    );
    await pdf(doc).toBlob();
    console.log('✓ Test 5 PASSED\n');
    return true;
  } catch (e) {
    console.log(`✗ Test 5 FAILED: ${e.message}\n`);
    return false;
  }
}

// Run tests sequentially
(async () => {
  if (!await test1()) return;
  if (!await test2()) return;
  if (!await test3()) return;
  if (!await test4()) return;
  if (!await test5()) return;
  console.log('✓ ALL TESTS PASSED - Issue must be in grouping logic or ContextSection');
})();
