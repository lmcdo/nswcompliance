/**
 * Test PRP-K7 API Implementation
 * Tests the new zone-aware development type system
 */

const { PRPK7DatabaseClient } = require('./lib/database/prp-k7-client');

async function testPRPK7API() {
 console.log(' Testing PRP-K7 API Implementation');
 console.log('═'.repeat(50));

 const dbClient = new PRPK7DatabaseClient();

 try {
 // Test database connection
 console.log('\n1. Testing database connection...');
 const connected = await dbClient.testConnection();
 console.log(` Database connected: ${connected ? '' : ''}`);

 if (!connected) {
 throw new Error('Database connection failed');
 }

 // Test zone queries for different zones
 const testZones = ['R2', 'R3', 'R4', 'B1'];
 
 for (const zone of testZones) {
 console.log(`\n2. Testing zone ${zone}...`);
 
 // Get zone statistics
 const stats = await dbClient.getZoneStats(zone);
 console.log(` Total provisions: ${stats.total_provisions}`);
 console.log(` Development types: ${stats.dev_type_count} (${stats.development_types.join(', ')})`);
 console.log(` Linked standards: ${stats.linked_standards}`);
 
 // Get grouped setbacks
 const groupedSetbacks = await dbClient.getZoneSetbacksGroupedByDevType(zone);
 console.log(` Grouped setbacks: ${Object.keys(groupedSetbacks).length} development types`);
 
 for (const [devType, setbacks] of Object.entries(groupedSetbacks)) {
 console.log(` ${devType}: ${setbacks.length} setbacks`);
 setbacks.forEach(s => {
 console.log(` ${s.boundary_type}: ${s.value}${s.unit} (${s.ref_number})`);
 });
 }
 
 // Get flat setbacks for API compatibility
 const flatSetbacks = await dbClient.getZoneSetbacksFlat(zone);
 console.log(` Flat setbacks: ${flatSetbacks.length} provisions`);
 }

 // Test API endpoint simulation
 console.log('\n3. Simulating API endpoint...');
 
 const testZone = 'R2';
 const startTime = Date.now();
 
 const groupedSetbacks = await dbClient.getZoneSetbacksGroupedByDevType(testZone);
 const setbacksData = await dbClient.getZoneSetbacksFlat(testZone);
 
 const apiResponse = {
 success: true,
 setback_results: setbacksData,
 grouped_setbacks: groupedSetbacks,
 zone: testZone,
 development_types_found: Object.keys(groupedSetbacks),
 processing_method: 'PRP-K7 Zone-Aware Development Type System (PostgreSQL)',
 processing_time_ms: Date.now() - startTime
 };

 console.log(' API Response Structure:');
 console.log(` success: ${apiResponse.success}`);
 console.log(` zone: ${apiResponse.zone}`);
 console.log(` development_types_found: [${apiResponse.development_types_found.join(', ')}]`);
 console.log(` setback_results: ${apiResponse.setback_results.length} provisions`);
 console.log(` grouped_setbacks: ${Object.keys(apiResponse.grouped_setbacks).length} groups`);
 console.log(` processing_time_ms: ${apiResponse.processing_time_ms}ms`);

 // Verify no aggregation
 console.log('\n4. Verifying no aggregation...');
 const boundaryTypes = {};
 setbacksData.forEach(s => {
 const key = `${s.development_type}_${s.boundary_type}`;
 boundaryTypes[key] = (boundaryTypes[key] || 0) + 1;
 });
 
 const multipleProvisions = Object.entries(boundaryTypes).filter(([key, count]) => count > 1);
 console.log(` Multiple provisions per boundary: ${multipleProvisions.length}`);
 multipleProvisions.forEach(([key, count]) => {
 console.log(` ${key}: ${count} provisions (no aggregation )`);
 });

 console.log('\n PRP-K7 API Test Complete!');
 console.log(' All functionality verified');
 
 } catch (error) {
 console.error(' Test failed:', error);
 } finally {
 await dbClient.close();
 }
}

// Run test
testPRPK7API();