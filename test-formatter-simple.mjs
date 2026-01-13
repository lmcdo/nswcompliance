/**
 * Simple test of the formatter with realistic provision text examples
 * Based on the actual HTML output issues the user reported
 */

import { parseProvisionText, stripSectionHeader } from './frontend-nextjs/lib/provision-text-formatter.ts';

console.log('Testing Provision Formatter\n');
console.log('='.repeat(80));

// Test Case 1: Section header duplication issue
// From user's HTML: section header appears both as <h3> and in body text
const test1 = {
  name: 'Section Header Duplication',
  raw: '4.1.1 Objectives\nO1 To provide buildings that respect character.\nO2 To enhance heritage.',
  sectionHeader: 'Objectives',
  expected: 'Should strip "4.1.1 Objectives" and render O1, O2 as controls'
};

console.log(`\nTEST 1: ${test1.name}`);
console.log('-'.repeat(80));
console.log('RAW:', test1.raw);
console.log('SECTION HEADER:', test1.sectionHeader);

const stripped1 = stripSectionHeader(test1.raw, test1.sectionHeader);
console.log('\nAFTER stripSectionHeader():', stripped1);

const parsed1 = parseProvisionText(stripped1, { skipHeadings: false });
console.log('\nPARSED ELEMENTS:');
parsed1.forEach((el, i) => {
  console.log(`  [${i}] ${el.type}: "${el.content}" ${el.marker ? `(marker: ${el.marker})` : ''}`);
});
console.log('\nEXPECTED:', test1.expected);

// Test Case 2: Numbered list inline vs newline
const test2 = {
  name: 'Numbered List Detection',
  raw: 'NB Refer to Section 2.1 for general controls. To achieve design excellence: 1. Consider the characteristics of the surrounding area 2. Ensure new development is compatible 3. Ensure the scale is appropriate',
  sectionHeader: null,
  expected: 'Should detect NB note + 3 separate list items'
};

console.log('\n' + '='.repeat(80));
console.log(`\nTEST 2: ${test2.name}`);
console.log('-'.repeat(80));
console.log('RAW:', test2.raw);

const stripped2 = stripSectionHeader(test2.raw, test2.sectionHeader);
console.log('\nAFTER stripSectionHeader():', stripped2);

const parsed2 = parseProvisionText(stripped2, { skipHeadings: false });
console.log('\nPARSED ELEMENTS:');
parsed2.forEach((el, i) => {
  console.log(`  [${i}] ${el.type}: "${el.content.slice(0, 60)}..." ${el.marker ? `(marker: ${el.marker})` : ''}`);
});
console.log('\nEXPECTED:', test2.expected);

// Test Case 3: Roman numerals without periods
const test3 = {
  name: 'Roman Numerals Without Periods',
  raw: 'The following design elements must be considered:\ni Overshadowing\nii Streetscape\niii Building setbacks',
  sectionHeader: null,
  expected: 'Should detect 3 roman numeral list items'
};

console.log('\n' + '='.repeat(80));
console.log(`\nTEST 3: ${test3.name}`);
console.log('-'.repeat(80));
console.log('RAW:', test3.raw);

const stripped3 = stripSectionHeader(test3.raw, test3.sectionHeader);
const parsed3 = parseProvisionText(stripped3, { skipHeadings: false });
console.log('\nPARSED ELEMENTS:');
parsed3.forEach((el, i) => {
  console.log(`  [${i}] ${el.type}: "${el.content}" ${el.marker ? `(marker: ${el.marker})` : ''}`);
});
console.log('\nEXPECTED:', test3.expected);

// Test Case 4: First paragraph bolding issue
// User said first paragraph is sometimes fully bolded when it shouldn't be
const test4 = {
  name: 'First Paragraph Should Not Be Bolded',
  raw: '4.1.8 Dormer windows\nThis section provides controls for dormer windows. Development must comply with the following requirements.',
  sectionHeader: 'Dormer windows',
  expected: 'Should have heading "4.1.8 Dormer windows", then 2 normal paragraphs (NOT bolded)'
};

console.log('\n' + '='.repeat(80));
console.log(`\nTEST 4: ${test4.name}`);
console.log('-'.repeat(80));
console.log('RAW:', test4.raw);

const stripped4 = stripSectionHeader(test4.raw, test4.sectionHeader);
console.log('\nAFTER stripSectionHeader():', stripped4);

const parsed4 = parseProvisionText(stripped4, { skipHeadings: false });
console.log('\nPARSED ELEMENTS:');
parsed4.forEach((el, i) => {
  console.log(`  [${i}] ${el.type}: "${el.content}"`);
});
console.log('\nEXPECTED:', test4.expected);

// Test Case 5: Section header includes body text
// User said "section header sometimes includes first words of following body text"
const test5 = {
  name: 'Section Header Capturing Body Text',
  raw: '4.1.9 Additional controls for contemporary dwellings within the Heritage Conservation Area',
  sectionHeader: 'Additional controls',
  expected: 'stripSectionHeader should only strip "4.1.9 Additional controls", NOT "for contemporary dwellings..."'
};

console.log('\n' + '='.repeat(80));
console.log(`\nTEST 5: ${test5.name}`);
console.log('-'.repeat(80));
console.log('RAW:', test5.raw);
console.log('SECTION HEADER:', test5.sectionHeader);

const stripped5 = stripSectionHeader(test5.raw, test5.sectionHeader);
console.log('\nAFTER stripSectionHeader():', stripped5);
console.log('\nEXPECTED:', test5.expected);
console.log('\nRESULT:', stripped5 === '4.1.9 Additional controls for contemporary dwellings within the Heritage Conservation Area' ? '❌ FAILED - Nothing was stripped!' : stripped5 === 'for contemporary dwellings within the Heritage Conservation Area' ? '✅ PASS' : '⚠️ UNEXPECTED');

console.log('\n' + '='.repeat(80));
console.log('\nSUMMARY OF ISSUES:\n');
console.log('1. stripSectionHeader() may not be stripping correctly');
console.log('2. Section headers might be appearing in both <h3> and body');
console.log('3. Inline numbered lists need better detection');
console.log('4. First paragraphs should never be bolded (only headings)');
console.log('5. Section headers must not capture following body text');
