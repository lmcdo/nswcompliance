const dbText = `4.1.8 Dormer windows

Dormers can be an effective way to make better use of existing space within the home.

The size and style of traditional dormers in the Marrickville LGA is varied.

Victorian and Federation style dormers are the most prevalent in the LGA, and they are generally plain with very little embellishment.

Controls

Dormer windows may be permitted on the front or side roof plane of any building, or row of buildings, where demonstrated to suit the style and age of the building/s they are associated with, and where compliant with C33-C40.`;

// Strip section header manually
const stripped = dbText.replace(/^4\.1\.8\s+Dormer windows\s*/, '').trim();

console.log('=== STEP BY STEP PREPROCESSING ===\n');

// Step 1: fixOcrSpacing (minimal version - just skip it for now since it's not exported)
let text = stripped;
console.log('1. After fixOcrSpacing():');
console.log(`Length: ${text.length}`);
console.log(`Contains "Controls": ${text.includes('Controls')}`);
console.log(`First 300 chars: ${text.substring(0, 300)}\n`);

// Step 2: NB preprocessing
const skipHeadings = false;
if (!skipHeadings) {
  text = text.replace(/([^\n])\s+(NB[:\.\s]|Note[:\s]|NOTE[:\s])/gi, '$1\n$2');
}
console.log('2. After NB preprocessing:');
console.log(`Contains "Controls": ${text.includes('Controls')}`);
console.log(`First 300 chars: ${text.substring(0, 300)}\n`);

// Step 3: List marker preprocessing
const preprocessed = text
  .replace(/\n(i{1,3}|iv|v|vi{1,3}|ix|x)\.\s*\n/gi, '\n$1. ')
  .replace(/\n([a-z])\.\s*\n/gi, '\n$1. ')
  .replace(/\n(\d+)\.\s*\n/g, '\n$1. ');

console.log('3. After list marker preprocessing:');
console.log(`Contains "Controls": ${preprocessed.includes('Controls')}`);
console.log(`First 300 chars: ${preprocessed.substring(0, 300)}\n`);

// Step 4: Split by newlines
const lines = preprocessed.split(/\n+/);
console.log('4. After split by /\\n+/:');
console.log(`Total lines: ${lines.length}\n`);

// Find the Controls line
const controlsLineIdx = lines.findIndex(l => l.trim() === 'Controls');
console.log(`Index of "Controls" line: ${controlsLineIdx}`);

if (controlsLineIdx >= 0) {
  console.log('\nContext around "Controls":');
  for (let i = Math.max(0, controlsLineIdx - 2); i <= Math.min(lines.length - 1, controlsLineIdx + 2); i++) {
    const marker = i === controlsLineIdx ? ' ← Controls' : '';
    console.log(`  Line ${i}: "${lines[i]}"${marker}`);
  }
} else {
  console.log('\n❌ "Controls" line NOT FOUND!');
  console.log('\nAll lines:');
  lines.forEach((l, i) => {
    console.log(`  Line ${i}: "${l.substring(0, 80)}${l.length > 80 ? '...' : ''}"`);
  });
}
