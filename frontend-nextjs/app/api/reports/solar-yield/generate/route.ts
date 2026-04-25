/**
 * POST /api/reports/solar-yield/generate
 * Body: { data: SolarYieldReportData } — full result from /api/satellite/solar-yield
 *
 * Computes financial ROI + solar grade, fetches aerial tile, renders the Solar Yield PDF.
 * Returns application/pdf stream.
 */

import { NextRequest, NextResponse } from 'next/server';
import { renderToBuffer } from '@react-pdf/renderer';
import React from 'react';
import {
  SolarYieldReportDocument,
  type SolarYieldReportData,
} from '@/lib/pdf/solar-yield-report';
import { getLogoBase64 } from '@/lib/pdf/logo';
import { fetchAerialTileBase64 } from '@/lib/pdf/aerial-tile';

export const dynamic = 'force-dynamic';
export const maxDuration = 30;

const RETAIL_RATE        = 0.32;
const FEED_IN_RATE       = 0.06;
const SELF_CONSUME_RATIO = 0.30;
const COST_PER_WATT      = 1.00;
const PANEL_WATTS        = 400;
const INVERTER_REPLACE   = 2000;

function calcROI(kwh: number, maxPanels: number) {
  const systemKw      = (maxPanels * PANEL_WATTS) / 1000;
  const selfKwh       = kwh * SELF_CONSUME_RATIO;
  const exportKwh     = kwh * (1 - SELF_CONSUME_RATIO);
  const annualSaving  = selfKwh * RETAIL_RATE + exportKwh * FEED_IN_RATE;
  const systemCost    = systemKw * 1000 * COST_PER_WATT;
  const paybackYears  = annualSaving > 0 ? systemCost / annualSaving : null;
  const tenYearReturn = annualSaving * 10 - systemCost - INVERTER_REPLACE;
  return { systemKw, annualSaving, systemCost, paybackYears, tenYearReturn };
}

function solarGrade(pitch: number, azimuth: number, sunshineHours: number): {
  grade: string; reason: string;
} {
  const pitchScore =
    pitch >= 15 && pitch <= 30 ? 3 :
    pitch >= 8  && pitch < 15  ? 2 :
    pitch >= 30 && pitch <= 40 ? 2 : 1;
  const northDev = Math.min(azimuth, 360 - azimuth);
  const azScore  =
    northDev <= 30 ? 3 : northDev <= 60 ? 2 : northDev <= 90 ? 1 : 0;
  const sunScore =
    sunshineHours >= 1700 ? 3 : sunshineHours >= 1500 ? 2 : sunshineHours >= 1300 ? 1 : 0;
  const total = pitchScore + azScore + sunScore;
  if (total >= 8) return { grade: 'A', reason: 'Excellent solar potential' };
  if (total >= 6) return { grade: 'B', reason: 'Good solar potential' };
  if (total >= 4) return { grade: 'C', reason: 'Moderate solar potential' };
  if (total >= 2) return { grade: 'D', reason: 'Below-average solar potential' };
  return              { grade: 'F', reason: 'Poor solar potential' };
}

export async function POST(req: NextRequest) {
  let body: { data?: unknown };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  if (!body?.data || typeof body.data !== 'object') {
    return NextResponse.json({ error: 'data is required' }, { status: 400 });
  }

  const raw = body.data as Record<string, unknown>;

  if (!raw.address) {
    return NextResponse.json({ error: 'data.address is required' }, { status: 400 });
  }

  const lat = typeof raw.lat === 'number' ? raw.lat : null;
  const lng = typeof raw.lng === 'number' ? raw.lng : null;

  const [tile_b64, logo_b64] = await Promise.all([
    (lat && lng) ? fetchAerialTileBase64(lat, lng) : Promise.resolve(null),
    Promise.resolve(getLogoBase64()),
  ]);

  // Pre-compute ROI and grade (same formulas as the tool component)
  const kwh        = Number(raw.annual_kwh_estimate ?? 0);
  const maxPanels  = Number(raw.max_panels ?? 0);
  const pitch      = Number(raw.best_pitch_deg ?? 0);
  const azimuth    = Number(raw.best_azimuth_deg ?? 0);
  const sunHours   = Number(raw.sunshine_hours_per_year ?? 0);

  const roi   = calcROI(kwh, maxPanels);
  const grade = solarGrade(pitch, azimuth, sunHours);

  const today = new Date().toISOString().split('T')[0];

  const data: SolarYieldReportData = {
    address: String(raw.address),
    run_date: String(raw.run_date ?? today),
    lat: lat ?? 0,
    lng: lng ?? 0,
    max_panels: maxPanels,
    max_panel_area_m2: Number(raw.max_panel_area_m2 ?? 0),
    annual_kwh_estimate: kwh,
    sunshine_hours_per_year: sunHours,
    best_pitch_deg: pitch,
    best_azimuth_deg: azimuth,
    roof_area_m2: Number(raw.roof_area_m2 ?? 0),
    is_heritage: Boolean(raw.is_heritage),
    is_commercial_scale: Boolean(raw.is_commercial_scale),
    imagery_date: String(raw.imagery_date ?? 'unknown'),
    coverage_available: Boolean(raw.coverage_available),
    // financial
    annual_saving_aud: roi.annualSaving,
    system_cost_aud: roi.systemCost,
    payback_years: roi.paybackYears,
    ten_year_return_aud: roi.tenYearReturn,
    system_kw: roi.systemKw,
    solar_grade: grade.grade,
    solar_grade_reason: grade.reason,
    // meta
    confidence: String(raw.confidence ?? 'medium'),
    data_sources: Array.isArray(raw.data_sources) ? (raw.data_sources as string[]) : [],
    tile_b64,
    logo_b64,
  };

  let pdfBuffer: Buffer;
  try {
    pdfBuffer = await renderToBuffer(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      React.createElement(SolarYieldReportDocument, { data }) as any
    );
  } catch (err) {
    console.error('[solar-yield/generate] PDF render error:', err);
    return NextResponse.json({ error: 'PDF generation failed' }, { status: 500 });
  }

  const slug = String(data.address).slice(0, 30).replace(/[^a-z0-9]/gi, '-').toLowerCase();
  const filename = `solar-yield-report-${slug}.pdf`;

  return new NextResponse(new Uint8Array(pdfBuffer), {
    status: 200,
    headers: {
      'Content-Type': 'application/pdf',
      'Content-Disposition': `attachment; filename="${filename}"`,
      'Content-Length': String(pdfBuffer.length),
    },
  });
}
