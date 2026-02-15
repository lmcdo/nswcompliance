// Test numeric provisions one by one to find the problematic one
import { pdf } from '@react-pdf/renderer';
import { createElement } from 'react';

const response = await fetch('http://localhost:3003/api/provisions/for-property?groupBy=toc&former_council=Marrickville&zone=R2&heritage=true&hca=Llewellyn+Estate+Heritage+Conservation+Area&precinct_id=15_');
const data = await response.json();

// Extract all provisions
const allProvisions = [];
if (data.success && data.data.by_layer) {
  for (const layer of data.data.by_layer) {
    allProvisions.push(...layer.provisions);
  }
}

// Filter for numeric provisions
const numericProvisions = allProvisions.filter(p => {
  const text = p.provision_text || '';
  const hasNumeric = /\d+(\.\d+)?\s*(m²|m|mm|cm|km|%|metres?|meters?|centimetres?|centimeters?)/i.test(text);
  const isObjective = /^O\d+|objective|principle|aim/i.test(text);
  return hasNumeric && !isObjective;
});

console.log(`Testing ${numericProvisions.length} numeric provisions...\n`);

// Check each provision for issues
const problematic = [];

for (const p of numericProvisions) {
  const issues = [];

  // Check page numbers
  if (p.pdf_page < 0) {
    issues.push(`pdf_page is negative: ${p.pdf_page}`);
  }
  if (p.pdf_printed_page < 0) {
    issues.push(`pdf_printed_page is negative: ${p.pdf_printed_page}`);
  }

  // Check for very large page numbers
  if (p.pdf_page > 1000) {
    issues.push(`pdf_page too large: ${p.pdf_page}`);
  }
  if (p.pdf_printed_page > 1000) {
    issues.push(`pdf_printed_page too large: ${p.pdf_printed_page}`);
  }

  // Check for NaN or null
  if (p.pdf_page && isNaN(p.pdf_page)) {
    issues.push(`pdf_page is NaN`);
  }
  if (p.pdf_printed_page && isNaN(p.pdf_printed_page)) {
    issues.push(`pdf_printed_page is NaN`);
  }

  // Check text length
  const text = p.provision_text || '';
  if (text.length > 15000) {
    issues.push(`text extremely long: ${text.length} chars`);
  }

  if (issues.length > 0) {
    problematic.push({
      id: p.id,
      pdf_page: p.pdf_page,
      pdf_printed_page: p.pdf_printed_page,
      text_length: text.length,
      issues: issues,
      preview: text.substring(0, 100)
    });
  }
}

console.log(`Found ${problematic.length} problematic provisions:\n`);
problematic.forEach(p => {
  console.log(`ID ${p.id}:`);
  console.log(`  pdf_page: ${p.pdf_page}, pdf_printed_page: ${p.pdf_printed_page}`);
  console.log(`  text_length: ${p.text_length}`);
  console.log(`  issues: ${p.issues.join(', ')}`);
  console.log(`  preview: ${p.preview}...`);
  console.log('');
});

// Also show provisions with negative page numbers specifically
const negativePages = numericProvisions.filter(p => p.pdf_page < 0 || p.pdf_printed_page < 0);
console.log(`\nProvisions with negative page numbers: ${negativePages.length}`);
negativePages.forEach(p => {
  console.log(`  ID ${p.id}: pdf_page=${p.pdf_page}, pdf_printed_page=${p.pdf_printed_page}`);
});
