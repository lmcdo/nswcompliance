import { parseProvisionText, stripSectionHeader } from './frontend-nextjs/lib/provision-text-formatter.ts';

// Real text from provision 78509
const realText = `4.1.8 Dormer windows

Dormers can be an effective way to make better use of existing space within the home.

The size and style of traditional dormers in the Marrickville LGA is varied. The appropriate size and style of a dormer is determined by the style and size of the dwelling, and often the detail of original dormers in the vicinity. Dormers can be found on Colonial, Victorian and Federation era dwelling houses. However each stylistic era requires dormers appropriate to its style. Dormers are generally not appropriate on Inter War period houses.

Victorian and Federation style dormers are the most prevalent in the LGA, and they are generally plain with very little embellishment.

Controls

Dormer windows may be permitted on the front or side roof plane of any building, or row of buildings, where demonstrated to suit the style and age of the building/s they are associated with, and where compliant with C33-C40.

Dormers must be positioned to minimise interruption of skyline views of chimneys and other original roof features when viewed from the street.

New dormers added to existing buildings shall adopt the style of traditional models on similar styled buildings in the neighbourhood.

Appropriate number of dormers:

i. only one dormer will be permitted in a Victorian single storey, single fronted dwelling, or a single fronted, two storey dwelling, with one level 1 window or door. (Figure 5)

ii. Only two front facing dormers will be permitted in a Victorian single storey, double fronted dwelling i.e. with central door and one window on either side (Figure 6), or a two storey Victorian dwelling with two sets of verandah doors at level 1. (Figure 7)

The style, shape and size of dormers proposed at the rear, or low impact location, of residential period buildings, may also be required to be traditional in style and will be assessed on merit.

Victorian dormer windows at the front must be:

i. Vertically proportioned (between a height to width ratio of 1.6:1 and 2:1);
ii. The same pitch and roof material as the main roof;
iii. Subordinate in size and position to the main roof, and be positioned at 300mm below the ridge, measured vertically;`;

console.log('=== TESTING REAL PROVISION TEXT ===\n');

// Test 1: stripSectionHeader
const sectionHeader = 'Dormer windows';
const stripped = stripSectionHeader(realText, sectionHeader);
console.log('Test 1: stripSectionHeader()');
console.log('Input section_header:', sectionHeader);
console.log('Stripped starts with:', stripped.substring(0, 100));
console.log('Successfully stripped header?', !stripped.startsWith('4.1.8'));
console.log();

// Test 2: parseProvisionText
const elements = parseProvisionText(stripped);
console.log('Test 2: parseProvisionText()');
console.log(`Total elements: ${elements.length}`);
console.log();

// Check for "Controls" subheading
const controlsElement = elements.find(el => el.type === 'subheading' && el.content === 'Controls');
console.log('Found "Controls" subheading?', !!controlsElement);
if (controlsElement) {
  console.log('Controls element:', JSON.stringify(controlsElement, null, 2));
} else {
  console.log('ERROR: "Controls" subheading NOT detected!');
  console.log('\nElements found:');
  elements.forEach((el, i) => {
    console.log(`${i}: ${el.type} - ${el.content?.substring(0, 80)}`);
  });
}
console.log();

// Check for list items
const listItems = elements.filter(el => el.type === 'list-item');
console.log(`Found ${listItems.length} list items`);
if (listItems.length > 0) {
  console.log('First 3 list items:');
  listItems.slice(0, 3).forEach(item => {
    console.log(`  ${item.marker} ${item.content?.substring(0, 60)}`);
  });
}
