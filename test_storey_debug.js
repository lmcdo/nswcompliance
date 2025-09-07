// Test to debug storey data in API response
fetch('http://localhost:3007/api/setbacks/calculate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    property_id: 1947493,
    property_zone: 'R1',
    lot_geometry: {
      rings: [[[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]]],
      hasM: false,
      hasZ: false,
      spatialReference: { wkid: 4326 }
    }
  })
})
.then(response => response.json())
.then(data => {
  console.log('=== API RESPONSE ===');
  console.log(JSON.stringify(data, null, 2));
  
  if (data.setback_results && data.setback_results.length > 0) {
    console.log('=== FIRST SETBACK RESULT FIELDS ===');
    console.log(Object.keys(data.setback_results[0]));
    
    console.log('=== FIRST SETBACK RESULT ===');
    console.log(JSON.stringify(data.setback_results[0], null, 2));
    
    // Check for storey fields specifically
    const result = data.setback_results[0];
    console.log('=== STOREY FIELDS CHECK ===');
    console.log('result.storeys:', result.storeys);
    console.log('result.storey_conditions:', result.storey_conditions);
    console.log('result.building_height_storeys:', result.building_height_storeys);
    console.log('result.conditions:', result.conditions);
  }
})
.catch(error => console.error('Error:', error));