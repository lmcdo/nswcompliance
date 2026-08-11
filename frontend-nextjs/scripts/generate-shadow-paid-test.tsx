/**
 * Generate a comprehensive paid Shadow report PDF for testing.
 * Run with: npx tsx scripts/generate-shadow-paid-test.tsx
 */

import { renderToBuffer } from '@react-pdf/renderer';
import React from 'react';
import fs from 'fs';
import path from 'path';
import { ShadowReportDocument, ShadowReportData } from '../lib/pdf/shadow-report';
import { getLogoBase64 } from '../lib/pdf/logo';

const data: ShadowReportData = {
  address: '25 Bondi Road, Bondi Junction NSW 2022',
  run_date: '2026-05-11',
  lat: -33.8932,
  lng: 151.2500,
  zone: 'R3',
  lga_name: 'Waverley',
  height_m: 12.0,
  height_source: 'lep',
  lep_name: 'Waverley Local Environmental Plan 2012',
  construction_change_score: 0.187,
  construction_change_detected: true,
  adg_compliant: false,
  worst_case_scenario: 'jun21_9am',
  confidence: 'high',
  data_sources: [
    'NSW Planning Portal API',
    'Sentinel-2 (Copernicus)',
    'NSW DEM (LPI LiDAR)',
    'NREL Solar Position Algorithm',
    'NSW Digital Cadastre (DCDB)',
  ],
  warnings: [
    'Construction activity detected on adjacent lot — BSI change score 0.187 exceeds threshold 0.120.',
    'LEP height limit of 12m allows buildings that may impact ADG solar access on this lot.',
  ],
  lot_polygon: {
    type: 'Polygon',
    coordinates: [[
      [151.2495, -33.8928],
      [151.2505, -33.8928],
      [151.2505, -33.8936],
      [151.2495, -33.8936],
      [151.2495, -33.8928],
    ]],
  },
  north_proxy_polygon: {
    type: 'Polygon',
    coordinates: [[
      [151.2495, -33.8920],
      [151.2505, -33.8920],
      [151.2505, -33.8928],
      [151.2495, -33.8928],
      [151.2495, -33.8920],
    ]],
  },
  is_paid: true,
  tile_b64: null,
  logo_b64: getLogoBase64(),
  qr_b64: null,
  firm_name: null,
  shareable_url: null,
  scenarios: [
    {
      scenario: 'jun21_9am',
      label: '21 Jun — 9:00 am (winter)',
      date: '2026-06-21',
      time_local: '09:00',
      shadow_length_m: 28.4,
      shadow_overlap_fraction: 0.72,
      shadow_direction_deg: 225,
      overlaps_subject_lot: true,
      shadow_on_lot: null,
      shadow_polygon: null,
    },
    {
      scenario: 'jun21_12pm',
      label: '21 Jun — 12:00 pm (winter)',
      date: '2026-06-21',
      time_local: '12:00',
      shadow_length_m: 18.6,
      shadow_overlap_fraction: 0.45,
      shadow_direction_deg: 180,
      overlaps_subject_lot: true,
      shadow_on_lot: null,
      shadow_polygon: null,
    },
    {
      scenario: 'jun21_3pm',
      label: '21 Jun — 3:00 pm (winter)',
      date: '2026-06-21',
      time_local: '15:00',
      shadow_length_m: 31.2,
      shadow_overlap_fraction: 0.68,
      shadow_direction_deg: 135,
      overlaps_subject_lot: true,
      shadow_on_lot: null,
      shadow_polygon: null,
    },
    {
      scenario: 'sep21_12pm',
      label: '21 Sep — 12:00 pm (equinox)',
      date: '2026-09-21',
      time_local: '12:00',
      shadow_length_m: 11.3,
      shadow_overlap_fraction: 0.18,
      shadow_direction_deg: 178,
      overlaps_subject_lot: false,
      shadow_on_lot: null,
      shadow_polygon: null,
    },
    {
      scenario: 'dec21_12pm',
      label: '21 Dec — 12:00 pm (summer)',
      date: '2026-12-21',
      time_local: '12:00',
      shadow_length_m: 5.1,
      shadow_overlap_fraction: 0.04,
      shadow_direction_deg: 175,
      overlaps_subject_lot: false,
      shadow_on_lot: null,
      shadow_polygon: null,
    },
  ],
};

async function main() {
  console.log('Rendering Shadow paid report...');
  const buffer = await renderToBuffer(
    React.createElement(ShadowReportDocument, { data })
  );
  const outPath = path.resolve('C:/Users/lawre/Downloads/shadow-paid-test.pdf');
  fs.writeFileSync(outPath, buffer);
  console.log(`Saved to ${outPath} (${(buffer.length / 1024).toFixed(1)} KB)`);
}

main().catch((err) => {
  console.error('Failed:', err);
  process.exit(1);
});
