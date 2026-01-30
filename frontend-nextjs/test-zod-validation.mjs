/**
 * Test Zod Validation Implementation
 * Validates that all 8 high-risk routes have proper Zod validation
 */

import fs from 'fs';
import path from 'path';

const routes = [
  {
    name: 'Compliance Enhanced',
    path: 'app/api/compliance/enhanced/route.ts',
    schema: 'ComplianceEnhancedSchema',
    method: 'POST'
  },
  {
    name: 'Property Search',
    path: 'app/api/property/route.ts',
    schema: 'PropertySearchSchema',
    method: 'GET'
  },
  {
    name: 'Capacity Calculate',
    path: 'app/api/capacity/calculate/route.ts',
    schema: 'CapacityCalculationSchema',
    method: 'POST'
  },
  {
    name: 'Provisions Search',
    path: 'app/api/provisions/route.ts',
    schema: 'ProvisionSearchSchema',
    method: 'GET'
  },
  {
    name: 'Live Check',
    path: 'app/api/compliance/live-check/route.ts',
    schema: 'LiveCheckSchema',
    method: 'POST'
  },
  {
    name: 'Permissibility Check',
    path: 'app/api/permissibility/check/route.ts',
    schema: 'ComplianceCheckSchema',
    method: 'POST'
  },
  {
    name: 'Housing SEPP',
    path: 'app/api/housing-sepp/eligibility/route.ts',
    schema: 'HousingSEPPSchema',
    method: 'POST'
  },
  {
    name: 'Precinct Provisions',
    path: 'app/api/precinct/provisions/route.ts',
    schema: 'ProvisionLookupSchema',
    method: 'POST'
  }
];

console.log('Verifying Zod validation implementation...\n');

let passed = 0;
let failed = 0;

for (const route of routes) {
  const filePath = path.join(process.cwd(), route.path);

  try {
    const content = fs.readFileSync(filePath, 'utf-8');

    const checks = {
      hasImport: content.includes(`import {`) && content.includes(`validateRequest`) && content.includes(`formatValidationErrors`),
      hasSchema: content.includes(route.schema),
      hasValidation: content.includes('validateRequest(') && content.includes(route.schema),
      hasErrorResponse: content.includes('formatValidationErrors'),
      hasValidationCheck: content.includes('if (!validation.success)'),
      hasValidatedData: content.includes('validation.data')
    };

    const allChecks = Object.values(checks).every(check => check);

    if (allChecks) {
      console.log(`✅ ${route.name} (${route.method})`);
      console.log(`   - Schema: ${route.schema}`);
      console.log(`   - All validation checks passed`);
      passed++;
    } else {
      console.log(`❌ ${route.name} (${route.method})`);
      console.log(`   - Schema: ${route.schema}`);
      console.log(`   - Missing checks:`, Object.entries(checks).filter(([_, v]) => !v).map(([k]) => k));
      failed++;
    }
    console.log('');

  } catch (error) {
    console.log(`❌ ${route.name} - File not found or error reading`);
    failed++;
    console.log('');
  }
}

console.log('='.repeat(60));
console.log(`Summary: ${passed} passed, ${failed} failed out of ${routes.length} routes`);

if (failed === 0) {
  console.log('✅ All routes have proper Zod validation!');
  process.exit(0);
} else {
  console.log('❌ Some routes are missing Zod validation');
  process.exit(1);
}
