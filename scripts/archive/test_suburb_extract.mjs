// Test suburb extraction logic directly

const SUBURB_NEARBY_MAP = {
  'annandale': ['annandale', 'stanmore', 'enmore', 'st peters', 'marrickville'],
  'stanmore': ['stanmore', 'annandale', 'enmore', 'petersham', 'marrickville'],
  'leichhardt': ['leichhardt', 'lilyfield', 'rozelle', 'annandale', 'haberfield'],
  'lilyfield': ['lilyfield', 'leichhardt', 'rozelle', 'annandale', 'balmain'],
  'rozelle': ['rozelle', 'lilyfield', 'leichhardt', 'balmain'],
  'marrickville': ['marrickville', 'petersham', 'stanmore', 'enmore', 'st peters'],
  'petersham': ['petersham', 'marrickville', 'stanmore', 'enmore'],
  'haberfield': ['haberfield', 'leichhardt', 'ashfield', 'five dock'],
};

function extractSuburbFromTitle(title) {
  const commaMatch = title.match(/,\s*([A-Za-z][A-Za-z\s]*?)(?:\s*$)/);
  if (commaMatch) return commaMatch[1].trim().toLowerCase();
  const atMatch = title.match(/\bat\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*$/);
  if (atMatch) return atMatch[1].trim().toLowerCase();
  return null;
}

function extractSuburbFromAddress(address) {
  // Try comma pattern first
  const commaMatch = address.match(/,\s*([A-Za-z][A-Za-z\s]*?)(?:\s+NSW|\s*$)/i);
  if (commaMatch) return commaMatch[1].trim().toLowerCase();
  // No-comma pattern: "185 PARRAMATTA ROAD ANNANDALE 2038"
  const noCommaMatch = address.match(/([A-Za-z]+(?:\s+[A-Za-z]+)?)\s+(?:NSW\s+)?\d{4}\s*$/i);
  if (noCommaMatch) {
    const words = noCommaMatch[1].trim().split(/\s+/);
    if (words.length === 2) {
      const streetTypes = ['road', 'street', 'avenue', 'drive', 'lane', 'way', 'place', 'court'];
      if (streetTypes.includes(words[0].toLowerCase())) {
        return words[1].toLowerCase();
      }
    }
    return words[words.length - 1].toLowerCase();
  }
  return null;
}

function isSuburbNearby(userSuburb, clauseSuburb) {
  if (userSuburb === clauseSuburb) return true;
  const nearbySet = SUBURB_NEARBY_MAP[userSuburb];
  if (nearbySet) return nearbySet.includes(clauseSuburb);
  const allInnerWestSuburbs = new Set(Object.keys(SUBURB_NEARBY_MAP));
  return allInnerWestSuburbs.has(clauseSuburb);
}

// Test cases
const tests = [
  { address: '185 PARRAMATTA ROAD ANNANDALE 2038', expected: 'annandale' },
  { address: '185 Parramatta Road, Annandale NSW 2038', expected: 'annandale' },
  { address: '1 Chester Street, Annandale NSW 2038', expected: 'annandale' },
];

console.log('=== extractSuburbFromAddress ===');
for (const t of tests) {
  const result = extractSuburbFromAddress(t.address);
  const ok = result === t.expected ? '✅' : '❌';
  console.log(`${ok} "${t.address}" => "${result}" (expected "${t.expected}")`);
}

console.log('\n=== extractSuburbFromTitle ===');
const titles = [
  { title: 'Development on land at 1 Llewellyn Street, Rhodes', expected: 'rhodes' },
  { title: 'Development of land at 1–5 Chester Street, Annandale', expected: 'annandale' },
  { title: 'Development of certain land within Zone B4 Mixed Use at Haberfield', expected: 'haberfield' },
  { title: 'Development on land at 126-134 Parramatta Road, Stanmore', expected: 'stanmore' },
  { title: 'Floor space ratio', expected: null },
];
for (const t of titles) {
  const result = extractSuburbFromTitle(t.title);
  const ok = result === t.expected ? '✅' : '❌';
  console.log(`${ok} "${t.title}" => "${result}" (expected "${t.expected}")`);
}

console.log('\n=== isSuburbNearby (annandale) ===');
const nearbyTests = [
  { suburb: 'rhodes', expected: false },
  { suburb: 'annandale', expected: true },
  { suburb: 'stanmore', expected: true },
  { suburb: 'leichhardt', expected: false },
  { suburb: 'petersham', expected: false },
];
for (const t of nearbyTests) {
  const result = isSuburbNearby('annandale', t.suburb);
  const ok = result === t.expected ? '✅' : '❌';
  console.log(`${ok} annandale near ${t.suburb}? ${result} (expected ${t.expected})`);
}

console.log('\n=== Full flow: 185 Parramatta Rd Annandale + clause 6.15 Rhodes ===');
const userSuburb = extractSuburbFromAddress('185 PARRAMATTA ROAD ANNANDALE 2038');
const clauseSuburb = extractSuburbFromTitle('Development on land at 1 Llewellyn Street, Rhodes');
console.log(`User suburb: "${userSuburb}"`);
console.log(`Clause suburb: "${clauseSuburb}"`);
if (clauseSuburb && userSuburb) {
  const nearby = isSuburbNearby(userSuburb, clauseSuburb);
  console.log(`isSuburbNearby: ${nearby}`);
  console.log(`Would filter? ${!nearby ? 'YES - skip this clause' : 'NO - include as nearby'}`);
} else {
  console.log('WARNING: suburb extraction failed, clause would NOT be filtered');
}
