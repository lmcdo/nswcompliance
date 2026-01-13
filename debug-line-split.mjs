import { stripSectionHeader } from './frontend-nextjs/lib/provision-text-formatter.ts';

const realText = `4.1.8 Dormer windows

Dormers can be an effective way to make better use of existing space within the home.

The size and style of traditional dormers in the Marrickville LGA is varied.

Victorian and Federation style dormers are the most prevalent in the LGA, and they are generally plain with very little embellishment.

Controls

Dormer windows may be permitted on the front or side roof plane of any building.`;

const sectionHeader = 'Dormer windows';
const stripped = stripSectionHeader(realText, sectionHeader);

console.log('=== ANALYZING LINE SPLITTING ===\n');
console.log('Stripped text first 500 chars:');
console.log(stripped.substring(0, 500));
console.log('\n=== LINES ===');

const lines = stripped.split(/\n/);
console.log(`Total lines: ${lines.length}\n`);

lines.forEach((line, i) => {
  const isControls = /^Controls?\s*$/i.test(line);
  console.log(`Line ${i}: [${line.length} chars] isControls=${isControls}`);
  console.log(`  Content: "${line}"`);
  console.log(`  Repr: ${JSON.stringify(line)}`);
  if (i < 12 || isControls) {
    console.log();
  }
});
