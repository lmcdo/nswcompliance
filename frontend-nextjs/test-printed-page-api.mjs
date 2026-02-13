/**
 * Test if production API returns pdf_printed_page for Marrickville heritage provisions
 */

const ADDRESS = "45 Victoria Road, Marrickville";
const API_URL = "https://verify.plotdetect.com.au/api/provisions/for-property";

console.log(`Testing API for address: ${ADDRESS}\n`);

const params = new URLSearchParams({
  address: ADDRESS,
  groupBy: 'topic',
  heritage: 'true',
  former_council: 'marrickville'
});

const response = await fetch(`${API_URL}?${params}`);
const data = await response.json();

if (!data.success) {
  console.error("API returned error:", data);
  process.exit(1);
}

// Debug: show all topics
console.log("Available topics:", Object.keys(data.data?.by_topic || {}));
console.log("Summary:", data.data?.summary);

// Check roof provisions (heritage provisions are grouped by their topic)
const roofProvisions = data.data?.by_topic?.roof || [];

console.log(`\nRoof provisions: ${roofProvisions.length}\n`);

if (roofProvisions.length > 0) {
  const first = roofProvisions[0];
  console.log("First Roof provision:");
  console.log(`  ID: ${first.id}`);
  console.log(`  v2_marker: ${first.v2_marker}`);
  console.log(`  pdf_page: ${first.pdf_page}`);
  console.log(`  pdf_printed_page: ${first.pdf_printed_page}`);
  console.log(`  Has pdf_printed_page field: ${first.hasOwnProperty('pdf_printed_page')}`);
  console.log(`  Expected printed page: ${first.pdf_page ? first.pdf_page - 14 : 'N/A'}`);
  console.log(`  Text preview: ${first.provision_text?.substring(0, 60)}...`);

  if (first.pdf_printed_page) {
    console.log(`\n✅ API IS returning pdf_printed_page = ${first.pdf_printed_page}`);
  } else {
    console.log(`\n❌ API is NOT returning pdf_printed_page (it's ${first.pdf_printed_page})`);
  }

  // Check a few more
  console.log("\n--- Checking first 5 roof provisions ---");
  roofProvisions.slice(0, 5).forEach((p, i) => {
    console.log(`${i+1}. ID ${p.id}: pdf_page=${p.pdf_page}, pdf_printed_page=${p.pdf_printed_page}, marker=${p.v2_marker}`);
  });
} else {
  console.log("No roof provisions found to test");
}

// Check if groupBy=toc works differently
console.log("\n--- Testing with groupBy=toc ---");
const tocParams = new URLSearchParams({
  address: ADDRESS,
  groupBy: 'toc',
  former_council: 'marrickville'
});

const tocResponse = await fetch(`${API_URL}?${tocParams}`);
const tocData = await tocResponse.json();

if (tocData.success) {
  const part8 = tocData.data?.by_toc?.['Part 8'];
  if (part8) {
    console.log(`Part 8 found with ${part8.provision_count} provisions`);
    // Find first provision with pdf_page
    for (const sectionId in part8.sections) {
      const section = part8.sections[sectionId];
      if (section.provisions && section.provisions.length > 0) {
        const prov = section.provisions[0];
        if (prov.pdf_page) {
          console.log(`  Sample provision ID ${prov.id}:`);
          console.log(`    pdf_page: ${prov.pdf_page}`);
          console.log(`    pdf_printed_page: ${prov.pdf_printed_page}`);
          break;
        }
      }
    }
  }
}
