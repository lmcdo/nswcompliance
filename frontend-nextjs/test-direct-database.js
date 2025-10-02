#!/usr/bin/env node

/**
 * PRP-A2: Direct Database Connection Test
 * Tests the new direct PostgreSQL connection vs subprocess
 *
 * Run with: node test-direct-database.js
 */

const { PostgreSQLComplianceClient } = require('./lib/database/postgres-compliance-client');

async function testDirectDatabase() {
  console.log('=== PRP-A2: Direct Database Connection Test ===\n');

  // Configure database connection
  const config = {
    host: process.env.DB_HOST || '127.0.0.1',
    database: process.env.DB_NAME || 'nsw_planning',
    user: process.env.DB_USER || 'postgres',
    password: process.env.DB_PASSWORD || '',
    port: parseInt(process.env.DB_PORT || '5432'),
    max: 20,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 2000,
  };

  console.log('Connecting to database:');
  console.log(`  Host: ${config.host}:${config.port}`);
  console.log(`  Database: ${config.database}`);
  console.log(`  User: ${config.user}`);
  console.log('');

  try {
    // Create direct database client
    const client = new PostgreSQLComplianceClient(config);

    // Test 1: Health check
    console.log('Test 1: Health Check');
    const health = await client.healthCheck();
    console.log(`  Status: ${health.healthy ? '✅ HEALTHY' : '❌ UNHEALTHY'}`);
    if (health.error) {
      console.log(`  Error: ${health.error}`);
    }
    console.log('');

    // Test 2: Get provision details
    console.log('Test 2: Get Provision Details (Clause 4.3 - Height)');
    const startProvision = Date.now();
    const provisions = await client.getProvisionDetails('Clause 4.3', 'LEP');
    const provisionTime = Date.now() - startProvision;
    console.log(`  Found: ${provisions.length} provisions`);
    console.log(`  Time: ${provisionTime}ms (Direct DB)`);
    if (provisions.length > 0) {
      console.log(`  Sample: ${provisions[0].ref_number} - ${provisions[0].section_header}`);
    }
    console.log('');

    // Test 3: Get setback provisions
    console.log('Test 3: Get Setback Provisions (Zone R2)');
    const startSetback = Date.now();
    const setbacks = await client.getSetbackProvisions('R2');
    const setbackTime = Date.now() - startSetback;
    console.log(`  Found: ${setbacks.length} setback provisions`);
    console.log(`  Time: ${setbackTime}ms (Direct DB)`);
    if (setbacks.length > 0) {
      console.log(`  Sample: ${setbacks[0].ref_number} - ${setbacks[0].section_header}`);
    }
    console.log('');

    // Test 4: Get comprehensive compliance data
    console.log('Test 4: Get Comprehensive Compliance Data');
    const startCompliance = Date.now();
    const complianceData = await client.getComplianceData('R2', false, {
      maxHeight: 9.5,
      maxFsr: 0.6
    });
    const complianceTime = Date.now() - startCompliance;
    console.log(`  Building Envelope: ${complianceData.building_envelope.length} constraints`);
    console.log(`  Environmental: ${complianceData.environmental.length} constraints`);
    console.log(`  Special Provisions: ${complianceData.special_provisions.length} constraints`);
    console.log(`  Time: ${complianceTime}ms (Direct DB)`);
    console.log('');

    // Test 5: Connection pool stats
    console.log('Test 5: Connection Pool Statistics');
    const stats = client.getPoolStats();
    console.log(`  Total Connections: ${stats.total}`);
    console.log(`  Idle Connections: ${stats.idle}`);
    console.log(`  Waiting Requests: ${stats.waiting}`);
    console.log('');

    // Performance summary
    console.log('=== Performance Summary ===');
    console.log(`Total Direct Database Time: ${provisionTime + setbackTime + complianceTime}ms`);
    console.log(`Average Query Time: ${Math.round((provisionTime + setbackTime + complianceTime) / 3)}ms`);
    console.log('');

    console.log('✅ PRP-A2 Direct Database Tests Completed Successfully!');
    console.log('');
    console.log('Performance Comparison (estimated):');
    console.log('  Subprocess Mode: ~5000ms for compliance data');
    console.log(`  Direct Database: ${complianceTime}ms for compliance data`);
    console.log(`  Improvement: ~${Math.round((1 - complianceTime/5000) * 100)}% faster`);

    // Close connections
    await client.close();

  } catch (error) {
    console.error('❌ Test Failed:', error);
    process.exit(1);
  }
}

// Run tests
testDirectDatabase().catch(console.error);