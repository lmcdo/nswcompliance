/**
 * Test the EXACT path the user described:
 * - Address: 45 Victoria Road, Marrickville
 * - DCP Tab -> Part 8 folder -> Heritage Layer -> Roof subtopic
 * - Should show page 6, but showing page 20
 */

const API_URL = "https://verify.plotdetect.com.au/api/provisions/for-property";

// Step 1: Get provisions for address with TOC grouping (Part 8 view)
const tocParams = new URLSearchParams({
  address: "45 Victoria Road, Marrickville",
  groupBy: "toc",
  former_council: "marrickville",
  heritage: "true"
});

console.log("Testing EXACT user path:");
console.log("1. Calling API with groupBy=toc (Part 8 folder view)\n");

const response = await fetch(`${API_URL}?${tocParams}`);
const data = await response.json();

if (!data.success) {
  console.error("API Error:", data);
  process.exit(1);
}

// Step 2: Check Part 8 provisions
const part8 = data.data?.by_toc?.["Part 8"];

if (!part8) {
  console.error("No Part 8 found in by_toc");
  console.log("Available parts:", Object.keys(data.data?.by_toc || {}));
  process.exit(1);
}

console.log(`Found Part 8: ${part8.provision_count} total provisions`);
console.log(`Sections in Part 8:`, Object.keys(part8.sections).join(", "));

// Step 3: Find Roof provisions in Part 8
let roofProvisions = [];
for (const [sectionId, section] of Object.entries(part8.sections)) {
  const roofProvsInSection = section.provisions.filter(p =>
    p.v2_topic?.toLowerCase() === 'roof' ||
    p.v2_heritage_element?.includes('roof')
  );
  if (roofProvsInSection.length > 0) {
    console.log(`\nSection "${section.section_title}" has ${roofProvsInSection.length} Roof provisions`);
    roofProvisions.push(...roofProvsInSection);
  }
}

if (roofProvisions.length === 0) {
  console.error("\nNo Roof provisions found in Part 8");
  process.exit(1);
}

console.log(`\nTotal Roof provisions in Part 8: ${roofProvisions.length}`);

// Step 4: Check the problematic provision (ID 78649, page 20 -> should be 6)
const problematic = roofProvisions.find(p => p.id === 78649);

if (problematic) {
  console.log("\n=== PROBLEMATIC PROVISION (ID 78649) ===");
  console.log(`pdf_page: ${problematic.pdf_page}`);
  console.log(`pdf_printed_page: ${problematic.pdf_printed_page}`);
  console.log(`Expected: pdf_printed_page should be 6`);
  console.log(`Text: ${problematic.provision_text?.substring(0, 60)}...`);

  if (problematic.pdf_printed_page === 6) {
    console.log("\n✅ API is returning correct pdf_printed_page = 6");
  } else {
    console.log(`\n❌ API returning wrong pdf_printed_page: ${problematic.pdf_printed_page}`);
  }
} else {
  console.log("\nProvision ID 78649 not found in this response");
}

// Step 5: Show sample of all roof provisions
console.log("\n=== FIRST 5 ROOF PROVISIONS ===");
roofProvisions.slice(0, 5).forEach(p => {
  console.log(`ID ${p.id}: pdf_page=${p.pdf_page}, pdf_printed_page=${p.pdf_printed_page}, v2_marker=${p.v2_marker}`);
});

console.log("\n=== TESTING COMPLETE ===");
console.log("If pdf_printed_page is correct but UI shows wrong number:");
console.log("→ The frontend component rendering Part 8 TOC view is not using pdf_printed_page");
