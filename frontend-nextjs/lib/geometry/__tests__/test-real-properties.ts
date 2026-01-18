/**
 * Manual test script for battleaxe detection with real properties
 *
 * Run with: npx ts-node --project tsconfig.json lib/geometry/__tests__/test-real-properties.ts
 *
 * This tests the algorithm against real cadastre geometry from NSW Planning Portal
 */

import { detectBattleaxeLot, analyzeLotShape } from '../lot-shape-analysis';
import { calculateLotDimensions } from '../lot-dimensions';

// Real property geometries would be fetched from API
// For manual testing, we simulate with realistic coordinates

// Test addresses that are likely battleaxe lots:
// - Properties with "A" suffix (e.g., "15A Smith St")
// - Rear lots (behind main street properties)
// - Small access lanes

// Sample real geometry from a rectangular lot (Hay St, Leichhardt)
const realRectangularLot = {
  hasM: false,
  hasZ: false,
  rings: [[
    [16831073.5, -3978543.2],
    [16831086.3, -3978543.8],
    [16831087.1, -3978499.2],
    [16831074.3, -3978498.6],
    [16831073.5, -3978543.2],
  ]],
  spatialReference: { wkid: 3857 }
};

// Simulated battleaxe lot geometry (based on typical Inner West rear lot)
// This represents a lot with ~4m wide handle and ~12m wide head
const simulatedBattleaxeLot = {
  hasM: false,
  hasZ: false,
  rings: [[
    // Handle bottom
    [16831050.0, -3978600.0],
    [16831055.0, -3978600.0],  // 5m wide handle
    // Handle going up
    [16831055.0, -3978575.0],  // 25m long handle
    // Transition to head
    [16831075.0, -3978575.0],
    [16831075.0, -3978545.0],  // Head top right
    [16831040.0, -3978545.0],  // Head top left
    [16831040.0, -3978575.0],  // Head bottom left
    [16831050.0, -3978575.0],  // Back to handle
    [16831050.0, -3978600.0],  // Close
  ]],
  spatialReference: { wkid: 3857 }
};

async function runTests() {
  console.log('='.repeat(60));
  console.log('BATTLEAXE DETECTION - REAL PROPERTY TESTS');
  console.log('='.repeat(60));

  // Test 1: Regular rectangular lot
  console.log('\n--- Test 1: Regular Rectangular Lot ---');
  const rectResult = detectBattleaxeLot(realRectangularLot as any);
  console.log('Is Battleaxe:', rectResult.isBattleaxe);
  console.log('Width Profile:', rectResult.widthProfile?.map(w => w.toFixed(1)).join(', '));

  const rectDims = calculateLotDimensions(realRectangularLot as any);
  console.log('Lot Dimensions:', {
    area: rectDims?.area,
    frontage: rectDims?.frontage,
    depth: rectDims?.depth,
    lotType: rectDims?.lotType,
  });

  // Test 2: Simulated battleaxe lot
  console.log('\n--- Test 2: Simulated Battleaxe Lot ---');
  const battleResult = detectBattleaxeLot(simulatedBattleaxeLot as any);
  console.log('Is Battleaxe:', battleResult.isBattleaxe);
  console.log('Confidence:', battleResult.confidence);
  console.log('Access Way Width:', battleResult.accessWayWidth, 'm');
  console.log('Access Way Length:', battleResult.accessWayLength, 'm');
  console.log('Main Lot Width:', battleResult.mainLotWidth, 'm');
  console.log('Main Lot Area:', battleResult.mainLotArea, 'm²');
  console.log('Meets SEPP Requirements:', battleResult.meetsMinimumRequirements);
  console.log('Compliance Issues:', battleResult.complianceIssues);
  console.log('Width Profile:', battleResult.widthProfile?.map(w => w.toFixed(1)).join(', '));

  const battleDims = calculateLotDimensions(simulatedBattleaxeLot as any);
  console.log('Full Lot Dimensions:', {
    area: battleDims?.area,
    frontage: battleDims?.frontage,
    depth: battleDims?.depth,
    lotType: battleDims?.lotType,
    battleaxe: battleDims?.battleaxe ? 'Detected' : 'Not detected',
  });

  // Test 3: Shape analysis
  console.log('\n--- Test 3: Shape Analysis ---');
  const rectShape = analyzeLotShape(realRectangularLot as any);
  console.log('Rectangular lot shape:', rectShape.lotType);

  const battleShape = analyzeLotShape(simulatedBattleaxeLot as any);
  console.log('Battleaxe lot shape:', battleShape.lotType);

  console.log('\n' + '='.repeat(60));
  console.log('TESTS COMPLETE');
  console.log('='.repeat(60));
}

runTests().catch(console.error);
