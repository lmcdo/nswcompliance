/**
 * Test integrated SEPP routing functionality
 * This tests the full TypeScript -> NSW API -> SEPP routing pipeline
 */

const { PropertyDataService } = require('../lib/property-data');
const { SeppRouter } = require('../lib/sepp-router');

async function testSeppRouting() {
    console.log('=== INTEGRATED SEPP ROUTING TEST ===');
    console.log('Testing: 3 WILKINSON LANE, TELOPEA NSW 2117');
    
    try {
        // Get property data which includes SEPP routing
        const propertyData = await PropertyDataService.getPropertyComplianceData(
            '3 WILKINSON LANE, TELOPEA NSW 2117'
        );
        
        console.log('\nProperty Data Retrieved:');
        console.log('Address:', propertyData.address);
        console.log('Zone:', propertyData.zoneDescription);
        console.log('Heritage:', propertyData.heritage?.isHeritage);
        
        console.log('\nSEPP Routing Result:');
        if (propertyData.seppRouting) {
            const routing = propertyData.seppRouting;
            console.log('Applicable SEPPs:', routing.applicableSepps);
            console.log('Total Files Matched:', routing.totalFiles);
            console.log('Missing SEPPs:', routing.missing);
            
            console.log('\nMatched Files:');
            for (const [seppId, files] of Object.entries(routing.seppFiles)) {
                console.log(`  ${seppId}:`);
                files.forEach(file => {
                    const filename = file.split(/[\\\/]/).pop();
                    console.log(`    - ${filename}`);
                });
            }
        } else {
            console.log('No SEPP routing data available');
        }
        
        // Test direct SeppRouter functionality
        console.log('\n=== DIRECT SEPP ROUTER TEST ===');
        const seppRouter = new SeppRouter();
        
        // Test with sample applicable SEPPs
        const testSepps = [
            'SEPP_HOUSING_2021',
            'SEPP_TRANSPORT_INFRASTRUCTURE_2021',
            'SEPP_SUSTAINABLE_BUILDINGS_2022',
            'SEPP_EXEMPT_COMPLYING_2008'
        ];
        
        const routingResult = seppRouter.routeApplicableSepps(testSepps);
        console.log('Test routing result:', routingResult);
        
    } catch (error) {
        console.error('Error during SEPP routing test:', error);
    }
}

// Run if called directly
if (require.main === module) {
    testSeppRouting()
        .then(() => {
            console.log('\n=== SEPP ROUTING TEST COMPLETE ===');
        })
        .catch(error => {
            console.error('Test failed:', error);
        });
}

module.exports = { testSeppRouting };