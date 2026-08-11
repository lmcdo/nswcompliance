/**
 * Standalone script to generate a paid Granny Flat report PDF.
 * Run: npx tsx scripts/generate-granny-pdf.ts
 */

import { renderToBuffer } from '@react-pdf/renderer';
import React from 'react';
import fs from 'fs';
import path from 'path';
import { GrannyFlatReportDocument, type GrannyFlatReportData } from '../lib/pdf/granny-flat-report';
import { getLogoBase64 } from '../lib/pdf/logo';

async function main() {
  const logo_b64 = getLogoBase64();

  const data: GrannyFlatReportData = {
    address: '14 Smith Street, Parramatta NSW 2150',
    run_date: '2026-05-11',
    lat: -33.8151,
    lng: 151.0011,
    // inputs
    lot_area_m2: 620,
    main_dwelling_area_m2: 180,
    confirmed_structure_count: 1,
    // outputs
    granny_flat_buildable: true,
    max_floor_area_m2: 60,
    estimated_weekly_rent_aud: 420,
    rental_yield_annual_pct: 5.8,
    assumed_build_cost_aud: 180000,
    confidence: 'high',
    confidence_reason: 'Lot meets all SEPP Housing 2021 criteria',
    warnings: [],
    data_sources: [
      'NSW Planning Portal (zone, overlays)',
      'NSW SIX Maps (lot boundary, area)',
      'NSW Fair Trading Rental Bond Data (Q1 2026)',
      'NSW Heritage Register',
      'SEPP (Housing) 2021',
      'City of Parramatta DCP 2023',
    ],
    // polygon — realistic lot shape around the address
    lot_polygon: {
      type: 'Polygon',
      coordinates: [[
        [151.0006, -33.8148],
        [151.0016, -33.8148],
        [151.0016, -33.8154],
        [151.0006, -33.8154],
        [151.0006, -33.8148],
      ]],
    },
    tile_b64: null,
    logo_b64,
    // LGA + DCP setbacks
    lga_name: 'City of Parramatta',
    lga_slug: 'parramatta',
    dcp_sd_setbacks: [
      { type: 'Front setback', requirement: 'Min 6 m', clause: 'cl 4.1.3.1', notes: 'Applies to all residential zones' },
      { type: 'Rear setback', requirement: 'Min 3 m', clause: 'cl 4.1.3.1', notes: '' },
      { type: 'Side setback', requirement: 'Min 0.9 m', clause: 'cl 4.1.3.1', notes: '1.5 m for walls above 7.2 m' },
      { type: 'Max height', requirement: '8.5 m', clause: 'cl 4.1.4', notes: '' },
      { type: 'Max site coverage', requirement: '50%', clause: 'cl 4.1.5', notes: 'Includes all structures on lot' },
      { type: 'Min landscaped area', requirement: '30% of site area', clause: 'cl 4.1.6', notes: '' },
      { type: 'Car parking', requirement: '1 space per secondary dwelling', clause: 'cl 4.5.2', notes: 'Not required under CDC pathway' },
      { type: 'Private open space', requirement: 'Min 24 m2', clause: 'cl 4.1.7', notes: 'Min dimension 3 m' },
      { type: 'Separation from dwelling', requirement: 'Min 3 m', clause: 'cl 4.1.3.2', notes: '' },
      { type: 'Max floor area', requirement: '60 m2', clause: 'cl 4.1.2', notes: 'Consistent with SEPP Housing 2021' },
    ],
    dcp_name: 'Parramatta DCP 2023',
    dcp_url: 'https://www.cityofparramatta.nsw.gov.au/development/planning-controls',
    // paid report fields
    is_paid: true,
    shareable_url: 'https://canibuildit.com.au/reports/granny-flat/test-uuid',
    qr_b64: null,
    firm_name: null,
  };

  console.log('Rendering PDF...');
  const buffer = await renderToBuffer(
    React.createElement(GrannyFlatReportDocument, { data })
  );

  const outPath = path.resolve('C:/Users/lawre/Downloads/granny-paid-test.pdf');
  fs.writeFileSync(outPath, buffer);
  console.log(`PDF saved to ${outPath} (${(buffer.length / 1024).toFixed(0)} KB)`);
}

main().catch((err) => {
  console.error('Failed to generate PDF:', err);
  process.exit(1);
});
