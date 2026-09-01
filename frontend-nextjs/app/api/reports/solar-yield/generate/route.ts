/**
 * POST /api/reports/solar-yield/generate
 *
 * Two call paths:
 *   A) Stripe webhook: { report_id } — fetches from property_reports, generates paid PDF
 *   B) Legacy direct:  { data, report_token } — verifies HMAC, generates free PDF
 *
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
import { verifyReport } from '@/lib/report-token';
import { generateQRBase64 } from '@/lib/pdf/qr';
import { createClient } from '@supabase/supabase-js';
import { deliveredKwhFrom } from '@/lib/solar/delivered';

const getSupabase = () => createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
);

export const dynamic = 'force-dynamic';
export const maxDuration = 30;

const RETAIL_RATE        = 0.32;
const FEED_IN_RATE       = 0.06;
const SELF_CONSUME_RATIO = 0.30;
const COST_PER_WATT      = 1.00;
const PANEL_WATTS        = 400;
const INVERTER_REPLACE   = 2000;

// NSW long-run average monthly share of annual irradiance (PVGIS, sums to ~1.0)
const MONTHLY_IRRADIANCE_SHARE = [
  0.099, 0.090, 0.091, 0.079, 0.068, 0.058,  // Jan–Jun
  0.065, 0.074, 0.082, 0.090, 0.095, 0.109,  // Jul–Dec
];

const SENSITIVITY_FEED_IN_RATES = [0.04, 0.06, 0.10];

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
  // No rate limit here — route is guarded by DB UUID (Path A) and HMAC (Path B).
  // The expensive Google Solar API call is already rate-limited at /api/satellite/solar-yield.
  // Applying satelliteRateLimiter here would cause webhook calls (which all come from the
  // same Vercel internal IP) to compete for the same 10/min bucket and fail above 10 sales/min.

  let body: { data?: unknown; is_paid?: boolean; report_token?: string; report_id?: string; firm_name?: string };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  let raw: Record<string, unknown>;
  let is_paid: boolean;

  // Path A: webhook call with report_id — fetch from DB, always paid
  if (body.report_id) {
    const { data: row, error } = await getSupabase()
      .from('property_reports')
      .select('address, lat, lng, run_date, outputs, confidence, data_sources')
      .eq('id', body.report_id.trim())
      .single();

    if (error || !row) {
      return NextResponse.json({ error: 'Report not found' }, { status: 404 });
    }

    const outputs = (row.outputs as Record<string, unknown>) ?? {};
    raw = {
      address: row.address,
      lat: row.lat,
      lng: row.lng,
      run_date: row.run_date,
      confidence: row.confidence,
      data_sources: row.data_sources,
      ...outputs,
    };
    is_paid = true;

  // Path B: direct call with data + HMAC token — free version
  } else {
    if (!body?.data || typeof body.data !== 'object') {
      return NextResponse.json({ error: 'report_id or data is required' }, { status: 400 });
    }
    raw = body.data as Record<string, unknown>;

    if (!raw.address) {
      return NextResponse.json({ error: 'data.address is required' }, { status: 400 });
    }

    const lat = typeof raw.lat === 'number' ? raw.lat : null;
    const lng = typeof raw.lng === 'number' ? raw.lng : null;

    if (lat === null || lng === null || !verifyReport(lat, lng, String(raw.address), String(raw.run_date ?? ''), body.report_token)) {
      return NextResponse.json({ error: 'Invalid or expired report token' }, { status: 403 });
    }
    const isAdmin = process.env.ADMIN_SECRET && req.headers.get('x-admin-key') === process.env.ADMIN_SECRET;
    is_paid = !!(isAdmin && body.is_paid === true);
  }

  const lat = typeof raw.lat === 'number' ? raw.lat : null;
  const lng = typeof raw.lng === 'number' ? raw.lng : null;

  const lotPoly = (raw.lot_polygon as { type: 'Polygon'; coordinates: number[][][] } | null) ?? null;

  const origin = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://verify.plotdetect.com.au';
  const shareable_url = body.report_id ? `${origin}/reports/solar-yield/${body.report_id}` : null;

  const [tile_b64, logo_b64, qr_b64] = await Promise.all([
    (lat && lng) ? fetchAerialTileBase64(lat, lng, 'property', lotPoly) : Promise.resolve(null),
    Promise.resolve(getLogoBase64()),
    shareable_url ? generateQRBase64(shareable_url) : Promise.resolve(null),
  ]);

  // Pre-compute ROI and grade (same formulas as the tool component)
  const kwhDc      = Number(raw.annual_kwh_estimate ?? 0);
  const maxPanels  = Number(raw.max_panels ?? 0);
  const pitch      = Number(raw.best_pitch_deg ?? 0);
  const azimuth    = Number(raw.best_azimuth_deg ?? 0);
  const sunHours   = Number(raw.sunshine_hours_per_year ?? 0);

  // MONEY IS COMPUTED FROM DELIVERED ENERGY, NOT DC.
  // Google Solar reports energy at the panel. Feeding that straight into the
  // ROI overstated the annual saving by 16.4%, showed payback at 6.4 years
  // against 7.5, and reported a ten-year return of $2,420 where the figure was
  // $671 — the system cost is subtracted afterwards, so the whole error lands
  // on the margin. The backend supplies annual_kwh_delivered; the fallback
  // applies the same published NREL PVWatts default rather than silently
  // reverting to DC if an older payload arrives.
  const kwh = deliveredKwhFrom(raw.annual_kwh_estimate, raw.annual_kwh_delivered) ?? 0;

  const roi   = calcROI(kwh, maxPanels);
  const grade = solarGrade(pitch, azimuth, sunHours);

  // Payback sensitivity: same system cost, 3 feed-in rate scenarios
  const sensitivity = SENSITIVITY_FEED_IN_RATES.map((feedIn) => {
    const selfKwh     = kwh * SELF_CONSUME_RATIO;
    const exportKwh   = kwh * (1 - SELF_CONSUME_RATIO);
    const annualSaving = selfKwh * RETAIL_RATE + exportKwh * feedIn;
    const paybackYears = annualSaving > 0 ? roi.systemCost / annualSaving : null;
    return { feed_in_rate: feedIn, annual_saving: Math.round(annualSaving), payback_years: paybackYears !== null ? Math.round(paybackYears * 10) / 10 : null };
  });

  // Monthly delivered kWh from annual × NSW irradiance distribution. Uses the
  // delivered figure so the twelve months sum to the number the money is based
  // on — a monthly chart in DC beside an annual saving in AC would not add up.
  const monthly_kwh = kwh > 0
    ? MONTHLY_IRRADIANCE_SHARE.map((share) => Math.round(kwh * share))
    : null;

  const today = new Date().toISOString().split('T')[0];

  const data: SolarYieldReportData = {
    address: String(raw.address),
    run_date: String(raw.run_date ?? today),
    lat: lat ?? 0,
    lng: lng ?? 0,
    max_panels: maxPanels,
    max_panel_area_m2: Number(raw.max_panel_area_m2 ?? 0),
    // Both, named for what they are. The report used to carry one number under
    // this key while the money was computed from it, so a reader could not tell
    // which basis they were looking at.
    annual_kwh_estimate: kwhDc,
    annual_kwh_delivered: Math.round(kwh),
    delivery_basis: raw.delivery_basis ? String(raw.delivery_basis) : null,
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
    // paid enhancements
    sensitivity,
    monthly_kwh,
    is_paid,
    neighbour_max_height_m: raw.neighbour_max_height_m != null ? Number(raw.neighbour_max_height_m) : null,
    lga_name: (raw.lga_name as string | null) ?? null,
    // meta
    confidence: String(raw.confidence ?? 'medium'),
    data_sources: Array.isArray(raw.data_sources) ? (raw.data_sources as string[]) : [],
    lot_polygon: (raw.lot_polygon as SolarYieldReportData['lot_polygon']) ?? null,
    tile_b64,
    logo_b64,
    qr_b64,
    firm_name: body.firm_name?.trim() || null,
    shareable_url,
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
