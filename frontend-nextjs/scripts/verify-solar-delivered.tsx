// prior-art-checked: reuse not viable because nothing renders a solar PDF from
// a REAL stored report. scripts/render-all-pdfs.tsx renders all seven reports
// from hand-written dummy data, which cannot exercise the fallback path this
// change turns on (stored rows carry annual_kwh_delivered = null). The flagged
// files share vocabulary only: verify-interest is an email capture route,
// db-verify is a connectivity probe, insert_solar_access_hours and
// spike_solar_samgeo are Python pipeline scripts, and the solar-potential page
// is a marketing surface. Four sweeps on origin/main 307c743f.
/**
 * Verify the delivered-energy change against a REAL stored report.
 *
 * Not dummy data: this pulls an actual row from property_reports, applies the
 * same derivation the generate route applies, prints what a reader will see,
 * and renders the real PDF so a crash cannot hide behind a passing unit test.
 *
 * Usage: npx tsx scripts/verify-solar-delivered.tsx
 */
import { renderToBuffer } from '@react-pdf/renderer';
import React from 'react';
import fs from 'fs';
import path from 'path';
import {
  SolarYieldReportDocument,
  type SolarYieldReportData,
} from '../lib/pdf/solar-yield-report';
import {
  deliveredKwhFrom,
  deliveryBasisText,
  DC_TO_DELIVERED,
} from '../lib/solar/delivered';

// Same constants the generate route declares.
const RETAIL_RATE = 0.32;
const FEED_IN_RATE = 0.06;
const SELF_CONSUME_RATIO = 0.3;
const COST_PER_WATT = 1.0;
const PANEL_WATTS = 400;
const INVERTER_REPLACE = 2000;

function calcROI(kwh: number, maxPanels: number) {
  const systemKw = (maxPanels * PANEL_WATTS) / 1000;
  const annualSaving =
    kwh * SELF_CONSUME_RATIO * RETAIL_RATE +
    kwh * (1 - SELF_CONSUME_RATIO) * FEED_IN_RATE;
  const systemCost = systemKw * 1000 * COST_PER_WATT;
  return {
    systemKw,
    annualSaving,
    systemCost,
    paybackYears: annualSaving > 0 ? systemCost / annualSaving : null,
    tenYearReturn: annualSaving * 10 - systemCost - INVERTER_REPLACE,
  };
}

async function main() {
  // The row is exported by psycopg2 rather than read through supabase-js,
  // because this Node build has no native WebSocket and the realtime client
  // refuses to construct. The DATA is identical — a real property_reports row.
  const src = path.join(process.cwd(), '.real-solar-report.json');
  if (!fs.existsSync(src)) {
    console.error(`${src} missing — export a REAL row first. Nothing verified.`);
    process.exit(2);
  }
  const row = JSON.parse(fs.readFileSync(src, 'utf-8'));

  const o = row.outputs as Record<string, any>;
  const dc = Number(o.annual_kwh_estimate);
  const delivered =
    deliveredKwhFrom(o.annual_kwh_estimate, o.annual_kwh_delivered) ?? 0;
  const roi = calcROI(delivered, Number(o.max_panels ?? 0));
  const old = calcROI(dc, Number(o.max_panels ?? 0));

  const line = (s: string) => console.log(s);
  line('='.repeat(74));
  line(`REAL STORED REPORT — ${row.address}`);
  line('='.repeat(74));
  line(`  id                   : ${row.id}`);
  line(`  annual_kwh_estimate  : ${dc.toLocaleString()}   (Google, DC at the panel)`);
  line(
    `  annual_kwh_delivered : ${
      o.annual_kwh_delivered ??
      'null — written before this change, so the FALLBACK path is what runs'
    }`,
  );
  line(`  max_panels           : ${o.max_panels}`);
  line('');
  line('--- what the reader now sees ------------------------------------------');
  line(
    `  ${Math.round(delivered).toLocaleString('en-AU')} kWh/yr delivered from ${roi.systemKw.toFixed(1)} kW system`,
  );
  line('');
  line(`  ${deliveryBasisText(o.annual_kwh_estimate)}`);
  line('');
  line('--- money, before and after -------------------------------------------');
  line(`                       was (DC)         now (delivered)`);
  line(
    `  annual saving    :  $${Math.round(old.annualSaving).toLocaleString().padEnd(14)} $${Math.round(roi.annualSaving).toLocaleString()}`,
  );
  line(
    `  payback          :  ${old.paybackYears!.toFixed(1)} yr`.padEnd(38) +
      `${roi.paybackYears!.toFixed(1)} yr`,
  );
  line(
    `  ten-year return  :  $${Math.round(old.tenYearReturn).toLocaleString().padEnd(14)} $${Math.round(roi.tenYearReturn).toLocaleString()}`,
  );
  line(`  factor applied   :  ${DC_TO_DELIVERED.toFixed(6)}`);

  const pdfData: SolarYieldReportData = {
    address: row.address,
    run_date: String(row.run_date ?? ''),
    lat: Number(row.lat ?? 0),
    lng: Number(row.lng ?? 0),
    max_panels: Number(o.max_panels ?? 0),
    max_panel_area_m2: Number(o.max_panel_area_m2 ?? 0),
    annual_kwh_estimate: dc,
    annual_kwh_delivered: Math.round(delivered),
    delivery_basis: o.delivery_basis ?? null,
    sunshine_hours_per_year: Number(o.sunshine_hours_per_year ?? 0),
    best_pitch_deg: Number(o.best_pitch_deg ?? 0),
    best_azimuth_deg: Number(o.best_azimuth_deg ?? 0),
    roof_area_m2: Number(o.roof_area_m2 ?? 0),
    is_heritage: Boolean(o.is_heritage),
    is_commercial_scale: Boolean(o.is_commercial_scale),
    imagery_date: String(o.imagery_date ?? 'unknown'),
    coverage_available: true,
    annual_saving_aud: Math.round(roi.annualSaving),
    system_cost_aud: Math.round(roi.systemCost),
    payback_years: roi.paybackYears,
    ten_year_return_aud: Math.round(roi.tenYearReturn),
    system_kw: roi.systemKw,
    solar_grade: 'B',
    solar_grade_reason: 'Good solar potential',
    sensitivity: [],
    monthly_kwh: null,
    is_paid: true,
    confidence: String(row.confidence ?? 'medium'),
    data_sources: (row.data_sources as string[]) ?? [],
    tile_b64: null,
    logo_b64: null,
  };

  const buf = await renderToBuffer(
    React.createElement(SolarYieldReportDocument, { data: pdfData }) as any,
  );
  const out = path.join(process.cwd(), 'solar-delivered-verify.pdf');
  fs.writeFileSync(out, buf);
  line('');
  line(`--- PDF rendered from the same data: ${(buf.length / 1024).toFixed(0)} KB -> ${out}`);
  line('    (rendering is the check — a crash here is what a unit test cannot see)');
}

main().catch((e) => {
  console.error('FAILED:', e);
  process.exit(1);
});
