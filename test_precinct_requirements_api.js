/**
 * Test the new precinct requirements API endpoint
 */

const testPrecinctAPI = async () => {
  console.log('=' + '='.repeat(79));
  console.log('TESTING PRECINCT REQUIREMENTS API');
  console.log('=' + '='.repeat(79));

  // Test 1: Query by precinct name
  console.log('\nTest 1: Query Abergeldie Estate by precinct name');
  const response1 = await fetch('http://localhost:3000/api/compliance/precinct-requirements', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      precinctName: 'Abergeldie Estate',
      lga: 'Inner West'
    })
  });

  const data1 = await response1.json();
  console.log('Success:', data1.success);
  console.log('Total Requirements:', data1.metrics?.total_requirements);
  console.log('High Confidence:', data1.metrics?.high_confidence_percent + '%');
  console.log('Categories:', data1.data?.categories?.length);

  if (data1.data?.categories) {
    console.log('\nCategories breakdown:');
    data1.data.categories.forEach(cat => {
      console.log(`  - ${cat.display_name}: ${cat.total_count} requirements (${cat.high_confidence_count} high conf)`);
    });
  }

  // Test 2: Show sample requirements
  if (data1.data?.categories && data1.data.categories.length > 0) {
    console.log('\nSample Requirements (first category):');
    const firstCategory = data1.data.categories[0];
    firstCategory.requirements.slice(0, 3).forEach(req => {
      console.log(`\n  Category: ${req.category}`);
      console.log(`  Text: ${req.requirement_text.substring(0, 100)}...`);
      console.log(`  Confidence: ${req.confidence}`);
      if (req.value_numeric) {
        console.log(`  Value: ${req.value_numeric} ${req.unit || ''}`);
      }
      console.log(`  Source Provisions: ${req.source_provision_ids.length}`);
    });
  }

  // Test 3: GET endpoint
  console.log('\n' + '='.repeat(80));
  console.log('Test 2: GET endpoint with query params');
  const response2 = await fetch('http://localhost:3000/api/compliance/precinct-requirements?precinctName=Barwon%20Park&lga=Inner%20West');

  const data2 = await response2.json();
  console.log('Success:', data2.success);
  console.log('Total Requirements:', data2.metrics?.total_requirements);
  console.log('Precinct:', data2.data?.precinct?.precinct_name);

  console.log('\n' + '='.repeat(80));
  console.log('API TESTS COMPLETE');
  console.log('=' + '='.repeat(79));
};

// Run tests if Next.js dev server is running
testPrecinctAPI().catch(err => {
  console.error('Test failed:', err.message);
  console.error('\nMake sure Next.js dev server is running:');
  console.error('  cd frontend-nextjs && npm run dev');
});
