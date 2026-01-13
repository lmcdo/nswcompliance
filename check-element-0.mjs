import fs from 'fs';
import { parseProvisionText, stripSectionHeader } from './frontend-nextjs/lib/provision-text-formatter.ts';

const fullText = fs.readFileSync('C:\\Users\\lawre\\AppData\\Local\\Temp\\provision-78509.txt', 'utf-8');
const startMarker = '================================================================================';
const endMarker = '================================================================================';
const start = fullText.indexOf(startMarker) + startMarker.length;
const end = fullText.lastIndexOf(endMarker);
const dbText = fullText.slice(start, end).trim();

const sectionHeader = 'Dormer windows';
const stripped = stripSectionHeader(dbText, sectionHeader);
const elements = parseProvisionText(stripped);

console.log('=== ELEMENT 0 FULL CONTENT ===\n');
console.log(elements[0].content);
console.log('\n\n=== ANALYSIS ===');
console.log(`Length: ${elements[0].content.length} characters`);
console.log(`Contains "Controls"? ${elements[0].content.includes('Controls')}`);

if (elements[0].content.includes('Controls')) {
  const idx = elements[0].content.indexOf('Controls');
  console.log(`Position of "Controls": ${idx}`);
  console.log(`\nContext (50 chars before and after):`);
  console.log(elements[0].content.substring(idx - 50, idx + 60));
}
