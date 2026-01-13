import fs from 'fs';
import { parseProvisionText, stripSectionHeader } from './frontend-nextjs/lib/provision-text-formatter.ts';

// Load full text from the file we saved earlier
const fullText = fs.readFileSync('C:\\Users\\lawre\\AppData\\Local\\Temp\\provision-78509.txt', 'utf-8');

// Extract just the provision_text_full (between the === markers)
const startMarker = '================================================================================';
const endMarker = '================================================================================';
const start = fullText.indexOf(startMarker) + startMarker.length;
const end = fullText.lastIndexOf(endMarker);
const dbText = fullText.slice(start, end).trim();

console.log('=== TESTING WITH FULL DATABASE TEXT ===\n');
console.log(`Total length: ${dbText.length} characters\n`);

// Step 1: stripSectionHeader
const sectionHeader = 'Dormer windows';
const stripped = stripSectionHeader(dbText, sectionHeader);

console.log('1. After stripSectionHeader():');
console.log(`Length: ${stripped.length}`);
console.log(`Starts with "Dormers"? ${stripped.startsWith('Dormers')}`);
console.log(`Contains "Controls"? ${stripped.includes('Controls')}`);

// Check for "Controls" on its own line
const lines = stripped.split(/\n/);
const controlsLines = lines.filter(l => l.trim() === 'Controls');
console.log(`Number of lines that are exactly "Controls": ${controlsLines.length}\n`);

// Step 2: parseProvisionText
const elements = parseProvisionText(stripped);

console.log('2. After parseProvisionText():');
console.log(`Total elements: ${elements.length}\n`);

// Find "Controls" subheading
const controlsElements = elements.filter(el => el.type === 'subheading' && /Controls/i.test(el.content || ''));
console.log(`Number of "Controls" subheading elements: ${controlsElements.length}\n`);

// Summary
console.log('First 10 elements:');
elements.slice(0, 10).forEach((el, i) => {
  const display = (el.content || el.marker || '').substring(0, 70);
  console.log(`${i}: ${el.type.padEnd(15)} - ${display}${display.length >= 70 ? '...' : ''}`);
});

if (elements.length > 10) {
  console.log(`\n... and ${elements.length - 10} more elements`);
}
