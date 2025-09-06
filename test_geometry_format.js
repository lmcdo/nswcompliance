// Test script to understand NSW API geometry format
// Run with: node test_geometry_format.js

const testGeometryPayload = {
  property_id: 123,
  lot_geometry: {
    hasM: false,
    hasZ: false,
    rings: [
      // Test different nesting levels to see which one works
      [
        // Level 3: coordinates as [x, y]
        [151.1, -33.9, 0],
        [151.2, -33.9, 0],
        [151.2, -33.8, 0],
        [151.1, -33.8, 0],
        [151.1, -33.9, 0]
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

console.log("Testing geometry format:");
console.log(JSON.stringify(testGeometryPayload, null, 2));

// Test the path that's failing: rings[0][0][0]
console.log("\nChecking path rings[0][0][0]:");
console.log("rings[0]:", typeof testGeometryPayload.lot_geometry.rings[0]);
console.log("rings[0][0]:", typeof testGeometryPayload.lot_geometry.rings[0][0]);
console.log("rings[0][0][0]:", typeof testGeometryPayload.lot_geometry.rings[0][0][0]);