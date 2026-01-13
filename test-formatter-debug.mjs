import fs from 'fs';

// Copy the parseProvisionText function but with logging
const realText = `4.1.8 Dormer windows

Dormers can be an effective way to make better use of existing space within the home.

The size and style of traditional dormers in the Marrickville LGA is varied.

Victorian and Federation style dormers are the most prevalent in the LGA, and they are generally plain with very little embellishment.

Controls

Dormer windows may be permitted on the front or side roof plane of any building, or row of buildings, where demonstrated to suit the style and age of the building/s they are associated with, and where compliant with C33-C40.

Dormers must be positioned to minimise interruption of skyline views of chimneys and other original roof features when viewed from the street.

Appropriate number of dormers:

i. only one dormer will be permitted in a Victorian single storey, single fronted dwelling.

ii. Only two front facing dormers will be permitted in a Victorian single storey, double fronted dwelling.`;

// Strip section header manually
const stripped = realText.replace(/^4\.1\.8\s+Dormer windows\s*\n/, '').trim();

console.log('=== STRIPPED TEXT ===');
console.log(stripped.substring(0, 500));
console.log('\n=== LINE ANALYSIS ===\n');

// Preprocessing (same as provision-text-formatter.ts lines 254-258)
const preprocessed = stripped
  .replace(/\n(i{1,3}|iv|v|vi{1,3}|ix|x)\.\s*\n/gi, '\n$1. ')
  .replace(/\n([a-z])\.\s*\n/gi, '\n$1. ')
  .replace(/\n(\d+)\.\s*\n/g, '\n$1. ');

console.log('After preprocessing:');
console.log(preprocessed.substring(0, 500));
console.log();

// Split by newlines
const lines = preprocessed.split(/\n+/);
console.log(`Total lines after split: ${lines.length}\n`);

// Analyze each line
const elements = [];
for (let i = 0; i < lines.length; i++) {
  const line = lines[i].trim();
  if (!line) {
    console.log(`Line ${i}: EMPTY - skipped`);
    continue;
  }

  console.log(`\nLine ${i}: "${line.substring(0, 80)}${line.length > 80 ? '...' : ''}"`);
  console.log(`  Length: ${line.length} chars`);

  // Test patterns in order (same as provision-text-formatter.ts)

  // 1. Section header pattern (lines 277-294)
  const sectionMatch = line.match(/^(\d+\.\d+(?:\.\d+)?)\s+(.+?)(?:\s*$)/);
  if (sectionMatch) {
    const titleText = sectionMatch[2];
    const wordCount = titleText.split(/\s+/).length;
    if (titleText.length <= 80 && wordCount <= 10) {
      console.log(`  ✓ SECTION HEADER: ${sectionMatch[1]} ${titleText}`);
      elements.push({ type: 'heading', content: line });
      continue;
    } else {
      console.log(`  ✗ Section match but too long (${titleText.length} chars, ${wordCount} words)`);
    }
  }

  // 2. NB pattern (lines 297-317)
  const nbPattern = /^(NB|Note|NOTE)[:\.\s]\s*([^.\n]+(?:\.[^.\n]+){0,1}\.?)/i;
  if (nbPattern.test(line)) {
    console.log(`  ✓ NB/NOTE pattern`);
    elements.push({ type: 'note', content: line });
    continue;
  }

  // 3. Controls/Objectives pattern (lines 320-328)
  if (/^Controls?\s*$/i.test(line) || /^Objectives?\s*$/i.test(line)) {
    console.log(`  ✓ CONTROLS/OBJECTIVES SUBHEADING`);
    elements.push({ type: 'subheading', content: line });
    continue;
  } else {
    console.log(`  ✗ Not Controls/Objectives (test: /^Controls?\\s*$/i)`);
  }

  // 4. Control marker at start (lines 331-343)
  const controlMatch = line.match(/^([CO]\d+)\s+(.+)/);
  if (controlMatch) {
    console.log(`  ✓ CONTROL MARKER at start: ${controlMatch[1]}`);
    elements.push({ type: 'control-marker', content: controlMatch[1] });
    continue;
  }

  // 5. Inline control marker (lines 346-370)
  const inlineControlMatch = line.match(/\b([CO]\d+)\b/);
  if (inlineControlMatch && !line.startsWith(inlineControlMatch[1])) {
    console.log(`  ✓ INLINE CONTROL MARKER: ${inlineControlMatch[1]} (not at start)`);
    elements.push({ type: 'control-marker', content: inlineControlMatch[1] });
    continue;
  }

  // 6. List item pattern (lines 373-386)
  const listMatch = line.match(/^((?:i{1,3}|iv|v|vi{1,3}|ix|x)\.?\s+|[•\-–*]\s*|[a-z][.)]\s*|\([a-z]\)\s*|\d+[.)]\s*|\(\d+\)\s*)(.+)/i);
  if (listMatch) {
    console.log(`  ✓ LIST ITEM: marker="${listMatch[1].trim()}"`);
    elements.push({ type: 'list-item', marker: listMatch[1].trim(), content: listMatch[2] });
    continue;
  }

  // 7. Default: paragraph
  console.log(`  → DEFAULT: paragraph`);
  elements.push({ type: 'paragraph', content: line });
}

console.log(`\n\n=== FINAL RESULTS ===`);
console.log(`Total elements: ${elements.length}`);
console.log('\nElements:');
elements.forEach((el, i) => {
  console.log(`${i}: ${el.type} - ${el.content?.substring(0, 60) || el.marker || ''}...`);
});

console.log(`\n\n=== CHECK: Would parseUnstructuredText() be called? ===`);
console.log(`elements.length = ${elements.length}`);
console.log(`text.length = ${stripped.length}`);
console.log(`Condition: elements.length <= 1 && text.length > 200`);
console.log(`Result: ${elements.length <= 1 && stripped.length > 200 ? 'YES - parseUnstructuredText() WOULD BE CALLED!' : 'NO'}`);
