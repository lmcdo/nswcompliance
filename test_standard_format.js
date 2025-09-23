// Test with the actual NSW API geometry format (standard ESRI)
const testData = {
 property_id: 34567,
 lot_geometry: {
 hasM: false,
 hasZ: false,
 rings: [
 [
 [16825650.35528102, -4015813.195964293],
 [16825642.37734708, -4015812.5034473557],
 [16825641.84557387, -4015818.5364726246],
 [16825638.252180707, -4015859.1205681264],
 [16825646.41078619, -4015859.7998498976],
 [16825650.35528102, -4015813.195964293]
 ]
 ],
 spatialReference: {
 wkid: 3857,
 latestWkid: null
 }
 },
 property_zone: "R1",
 lot_area: 500
};

console.log("Testing Standard ESRI format with real NSW coordinates:");

fetch('http://localhost:3002/api/setbacks/calculate', {
 method: 'POST',
 headers: {
 'Content-Type': 'application/json',
 },
 body: JSON.stringify(testData)
})
.then(response => response.json())
.then(data => {
 if (data.success) {
 console.log(' SUCCESS! Found', data.setback_results.length, 'setbacks');
 console.log('Processing time:', data.processing_time_ms + 'ms');
 console.log('Buildable area:', data.buildable_area_analysis.buildable_area + 'm²');
 } else {
 console.log(' FAILED:', data.error);
 }
})
.catch(error => {
 console.error(' REQUEST ERROR:', error);
});