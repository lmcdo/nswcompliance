import { parseProvisionText, stripSectionHeader } from './frontend-nextjs/lib/provision-text-formatter.ts';

// EXACT text from database (provision 78509)
const dbText = `4.1.8 Dormer windows

Dormers can be an effective way to make better use of existing space within the home.

The size and style of traditional dormers in the Marrickville LGA is varied.

Victorian and Federation style dormers are the most prevalent in the LGA, and they are generally plain with very little embellishment.

Controls

Dormer windows may be permitted on the front or side roof plane of any building, or row of buildings, where demonstrated to suit the style and age of the building/s they are associated with, and where compliant with C33-C40.`;

console.log('=== TESTING ACTUAL FUNCTIONS ===\n');

// Step 1: stripSectionHeader
const sectionHeader = 'Dormer windows';
const stripped = stripSectionHeader(dbText, sectionHeader);

console.log('1. After stripSectionHeader():');
console.log('First 200 chars:', stripped.substring(0, 200));
console.log('Starts with "Dormers"?', stripped.startsWith('Dormers'));
console.log('Contains "Controls"?', stripped.includes('Controls'));

// Check if "Controls" is on its own line
const lines = stripped.split(/\n/);
const controlsLine = lines.find(l => l.trim() === 'Controls');
console.log('Has line that is exactly "Controls"?', !!controlsLine);
if (controlsLine !== undefined) {
  const idx = lines.indexOf(controlsLine);
  console.log(`Found at line index: ${idx}`);
  console.log(`Line before: "${lines[idx - 1]}"`);
  console.log(`Line after: "${lines[idx + 1]}"`);
}
console.log();

// Step 2: parseProvisionText
const elements = parseProvisionText(stripped);

console.log('2. After parseProvisionText():');
console.log(`Total elements: ${elements.length}`);

// Find Controls subheading
const controlsElement = elements.find(el => el.type === 'subheading' && /Controls/i.test(el.content || ''));
console.log('Found Controls subheading?', !!controlsElement);

console.log('\nAll elements:');
elements.forEach((el, i) => {
  const display = (el.content || el.marker || '').substring(0, 80);
  console.log(`${i}: ${el.type.padEnd(15)} - ${display}${display.length >= 80 ? '...' : ''}`);
});
