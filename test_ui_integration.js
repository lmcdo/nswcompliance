#!/usr/bin/env node
/**
 * Test UI Integration with Phase 1A Legal References
 * ==================================================
 * 
 * This test verifies that:
 * 1. NextJS API route calls the domain-aware Python engine
 * 2. Legal authority data is properly formatted for UI display
 * 3. Domain classification prevents cross-contamination
 * 4. Frontend receives enhanced metadata
 */

const https = require('http');
const { URL } = require('url');

async function testUIIntegration() {
 console.log('[UI TEST] Testing Complete UI Integration with Legal References');
 console.log('='.repeat(70));
 
 const testCases = [
 {
 name: 'Marrickville Residential Property',
 address: '123 Test Street, Marrickville NSW 2204',
 expectedDomain: 'RESIDENTIAL_BUILDINGS',
 expectedAuthority: 'Inner West LEP 2022'
 },
 {
 name: 'Leichhardt Residential Property', 
 address: '456 Sample Road, Leichhardt NSW 2040',
 expectedDomain: 'RESIDENTIAL_BUILDINGS',
 expectedAuthority: 'Inner West LEP 2022'
 }
 ];
 
 for (let i = 0; i < testCases.length; i++) {
 const testCase = testCases[i];
 console.log(`\n[TEST ${i+1}] ${testCase.name}`);
 console.log('-'.repeat(50));
 
 try {
 const response = await makeAPIRequest(testCase.address);
 
 console.log(`[REQUEST] GET /api/compliance/setbacks?address=${encodeURIComponent(testCase.address)}`);
 console.log(`[STATUS] ${response.success ? 'SUCCESS' : 'FAILED'}`);
 
 if (response.success && response.setbacks) {
 // Test 1: Check if we got domain-aware results
 const hasEnhancedData = checkForEnhancedData(response);
 console.log(`[ENHANCED DATA] ${hasEnhancedData ? 'PRESENT' : 'MISSING'}`);
 
 // Test 2: Check for legal authority
 const hasLegalAuthority = checkForLegalAuthority(response);
 console.log(`[LEGAL AUTHORITY] ${hasLegalAuthority ? 'PRESENT' : 'MISSING'}`);
 
 // Test 3: Check for cross-contamination prevention
 const hasContaminationCheck = checkForContaminationPrevention(response);
 console.log(`[CONTAMINATION PREVENTION] ${hasContaminationCheck ? 'ACTIVE' : 'INACTIVE'}`);
 
 // Test 4: Verify no signage contamination
 const hasSignageContamination = checkForSignageContamination(response);
 console.log(`[SIGNAGE CONTAMINATION] ${hasSignageContamination ? 'DETECTED' : 'CLEAN'}`);
 
 // Display sample result
 displaySampleResult(response);
 
 // Overall test result
 const overallPass = hasEnhancedData && hasLegalAuthority && hasContaminationCheck && !hasSignageContamination;
 console.log(`[OVERALL] ${overallPass ? 'PASSED' : 'FAILED'}`);
 
 } else {
 console.log(`[ERROR] ${response.error || 'No setbacks returned'}`);
 console.log(`[PROCESSING METHOD] ${response.processing_method || 'Unknown'}`);
 }
 
 } catch (error) {
 console.log(`[ERROR] ${error.message}`);
 }
 }
 
 console.log(`\n[COMPLETE] UI Integration Testing Complete`);
 console.log('='.repeat(70));
}

function makeAPIRequest(address) {
 return new Promise((resolve, reject) => {
 const url = `http://localhost:3000/api/compliance/setbacks?address=${encodeURIComponent(address)}`;
 
 const req = https.get(url, (res) => {
 let data = '';
 
 res.on('data', (chunk) => {
 data += chunk;
 });
 
 res.on('end', () => {
 try {
 const response = JSON.parse(data);
 resolve(response);
 } catch (e) {
 reject(new Error(`Invalid JSON response: ${e.message}`));
 }
 });
 });
 
 req.on('error', (error) => {
 reject(error);
 });
 
 req.setTimeout(30000, () => {
 req.abort();
 reject(new Error('Request timeout'));
 });
 });
}

function checkForEnhancedData(response) {
 return response.processing_method === 'domain_aware_python' ||
 response.metadata?.domain_filtering_applied === true ||
 response.metadata?.signage_contamination_eliminated === true;
}

function checkForLegalAuthority(response) {
 if (response.setbacks && response.source_authority) {
 return response.source_authority === 'Inner West LEP 2022' ||
 response.legal_authority_verified === true;
 }
 return false;
}

function checkForContaminationPrevention(response) {
 return response.cross_contamination_prevented === true ||
 response.metadata?.domain_filtering_applied === true;
}

function checkForSignageContamination(response) {
 if (response.setbacks) {
 const setbacksText = JSON.stringify(response.setbacks).toLowerCase();
 return setbacksText.includes('sign') || 
 setbacksText.includes('advertising') ||
 setbacksText.includes('signage');
 }
 return false;
}

function displaySampleResult(response) {
 console.log('\n[SAMPLE RESULT]');
 
 if (response.setbacks) {
 // Show the first available setback
 const sampleBoundary = ['front', 'side', 'rear'].find(boundary => response.setbacks[boundary]);
 
 if (sampleBoundary && response.setbacks[sampleBoundary]) {
 const setback = response.setbacks[sampleBoundary];
 console.log(` Boundary: ${sampleBoundary}`);
 console.log(` Setback: ${setback.value}${setback.unit || 'm'}`);
 console.log(` Confidence: ${setback.confidence || 'N/A'}`);
 console.log(` Source: ${setback.source || 'N/A'}`);
 
 if (setback.domain_classification) {
 console.log(` Domain: ${setback.domain_classification}`);
 }
 
 if (setback.legal_authority) {
 console.log(` Legal Authority: ${setback.legal_authority.primary_authority}`);
 console.log(` Secondary Authority: ${setback.legal_authority.secondary_authority}`);
 }
 }
 }
 
 console.log(` Processing Method: ${response.processing_method || 'Unknown'}`);
 console.log(` Metadata: ${JSON.stringify(response.metadata || {}, null, 2).substring(0, 200)}...`);
}

// Run the test
testUIIntegration().catch(error => {
 console.error('[TEST FAILED]', error);
 process.exit(1);
});