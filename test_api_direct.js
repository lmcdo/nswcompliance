// Test direct API call with fetch to see the raw data being sent
const testData = {
  property_id: 123,
  lot_geometry: {
    hasM: false,
    hasZ: false,
    rings: [
      [
        [
          [151.1, -33.9, 0],  // Extra level of nesting - NSW API format
          [151.2, -33.9, 0],
          [151.2, -33.8, 0],
          [151.1, -33.8, 0],
          [151.1, -33.9, 0]
        ]
      ]
    ],
    spatialReference: {
      wkid: 4326,
      latestWkid: 4326
    }
  },
  property_zone: "R1",
  lot_area: 450
};

console.log("Testing API call with extra nesting level:");
console.log("rings[0][0][0]:", typeof testData.lot_geometry.rings[0][0][0]);
console.log("rings[0][0][0][0]:", typeof testData.lot_geometry.rings[0][0][0][0]);

fetch('http://localhost:3002/api/setbacks/calculate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(testData)
})
.then(response => response.json())
.then(data => {
  console.log('\nAPI Response:', data);
})
.catch(error => {
  console.error('\nAPI Error:', error);
});