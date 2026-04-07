'use client';

import { useState } from 'react';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';

interface SolarYieldOutputs {
  max_panels: number;
  max_panel_area_m2: number;
  annual_kwh_estimate: number;
  sunshine_hours_per_year: number;
  best_pitch_deg: number;
  best_azimuth_deg: number;
  roof_area_m2: number;
  is_heritage: boolean;
  imagery_date: string;
  coverage_available: boolean;
}

interface ReportData {
  product: string;
  address: string;
  lat: number;
  lng: number;
  run_date: string;
  outputs: SolarYieldOutputs;
  confidence: string;
  data_sources: string[];
}

type PageState = 'idle' | 'running' | 'complete' | 'error';

// ── Financial assumptions ────────────────────────────────────────────────────
const RETAIL_RATE        = 0.32;   // $/kWh — NSW mid-market, AER DMO 2025–26 reference
const FEED_IN_RATE       = 0.06;   // $/kWh — AER voluntary FiT benchmark NSW 2024–25
const SELF_CONSUME_RATIO = 0.30;   // 30% self-consumed — ARENA/CSIRO Solar Home study
const COST_PER_WATT      = 1.00;   // $/W installed after STCs — SolarQuotes NSW Q1 2026
const PANEL_WATTS        = 400;    // W — standard residential panel 2024–25
const INVERTER_REPLACE   = 2000;   // $ at year 10

function calcROI(kwh: number, maxPanels: number) {
  const systemKw  = (maxPanels * PANEL_WATTS) / 1000;
  const selfKwh   = kwh * SELF_CONSUME_RATIO;
  const exportKwh = kwh * (1 - SELF_CONSUME_RATIO);
  const annualSaving = selfKwh * RETAIL_RATE + exportKwh * FEED_IN_RATE;
  const systemCost   = systemKw * 1000 * COST_PER_WATT;
  const paybackYears = annualSaving > 0 ? systemCost / annualSaving : null;
  const tenYearReturn = annualSaving * 10 - systemCost - INVERTER_REPLACE;
  return { systemKw, annualSaving, systemCost, paybackYears, tenYearReturn };
}

// ── Solar suitability grade ──────────────────────────────────────────────────
function solarGrade(pitch: number, azimuth: number, sunshineHours: number): { grade: string; colour: string; reason: string } {
  // Pitch score: 15–30° is ideal for Sydney (~34°S latitude)
  const pitchScore =
    pitch >= 15 && pitch <= 30 ? 3 :
    pitch >= 8  && pitch < 15  ? 2 :
    pitch >= 30 && pitch <= 40 ? 2 : 1;

  // Azimuth score: north (0/360°) is ideal in Southern Hemisphere
  const northDev = Math.min(azimuth, 360 - azimuth); // deviation from north
  const azScore =
    northDev <= 30  ? 3 :
    northDev <= 60  ? 2 :
    northDev <= 90  ? 1 : 0;

  // Sunshine score
  const sunScore =
    sunshineHours >= 1700 ? 3 :
    sunshineHours >= 1500 ? 2 :
    sunshineHours >= 1300 ? 1 : 0;

  const total = pitchScore + azScore + sunScore;

  if (total >= 8) return { grade: 'A', colour: 'text-emerald-700 bg-emerald-50', reason: 'Excellent solar potential' };
  if (total >= 6) return { grade: 'B', colour: 'text-teal-700 bg-teal-50',       reason: 'Good solar potential' };
  if (total >= 4) return { grade: 'C', colour: 'text-yellow-700 bg-yellow-50',   reason: 'Moderate solar potential' };
  if (total >= 2) return { grade: 'D', colour: 'text-orange-700 bg-orange-50',   reason: 'Below-average solar potential' };
  return           { grade: 'F', colour: 'text-red-700 bg-red-50',               reason: 'Poor solar potential' };
}

function azimuthLabel(deg: number): string {
  if (deg >= 337.5 || deg < 22.5) return 'N';
  if (deg < 67.5) return 'NE';
  if (deg < 112.5) return 'E';
  if (deg < 157.5) return 'SE';
  if (deg < 202.5) return 'S';
  if (deg < 247.5) return 'SW';
  if (deg < 292.5) return 'W';
  return 'NW';
}

function fmt$(n: number) {
  return n.toLocaleString('en-AU', { style: 'currency', currency: 'AUD', maximumFractionDigits: 0 });
}

const GOOGLE_MAPS_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY ?? '';

function aerialTileUrl(lat: number, lng: number) {
  return `https://maps.googleapis.com/maps/api/staticmap?center=${lat},${lng}&zoom=19&size=600x300&maptype=satellite&key=${GOOGLE_MAPS_KEY}`;
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function SolarYieldPage() {
  const [address, setAddress] = useState('');
  const [state, setState] = useState<PageState>('idle');
  const [report, setReport] = useState<ReportData | null>(null);
  const [errorMsg, setErrorMsg] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!address.trim()) return;

    setState('running');
    setReport(null);
    setErrorMsg('');

    try {
      const res = await fetch('/api/satellite/solar-yield', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address }),
      });

      const json = await res.json();

      if (!res.ok) {
        throw new Error(json.error || 'Failed to run report');
      }

      setReport(json.data);
      setState('complete');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setErrorMsg(msg);
      setState('error');
    }
  };

  return (
    <div className="max-w-2xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Solar Potential Assessment</h1>
        <p className="mt-1.5 text-sm text-gray-500">
          Roof geometry, system sizing, financial return, and suitability grade for any NSW address.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex gap-3 mb-8">
        <AddressAutocomplete
          value={address}
          onChange={setAddress}
          onSelect={(addr) => setAddress(addr)}
          className="flex-1 px-4 py-2.5 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
          disabled={state === 'running'}
        />
        <button
          type="submit"
          disabled={state === 'running' || !address.trim()}
          className="px-5 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {state === 'running' ? 'Running...' : 'Run Report'}
        </button>
      </form>

      {state === 'running' && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 flex flex-col items-center text-center">
          <div className="w-8 h-8 border-2 border-teal-600 border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-sm font-medium text-gray-700">Analysing roof geometry...</p>
          <p className="text-xs text-gray-400 mt-1">Usually completes in 5–10 seconds.</p>
        </div>
      )}

      {state === 'error' && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-sm text-red-700">
          {errorMsg}
        </div>
      )}

      {state === 'complete' && report && (
        <ReportCard report={report} />
      )}
    </div>
  );
}

// ── Report card ───────────────────────────────────────────────────────────────

function ReportCard({ report }: { report: ReportData }) {
  const o = report.outputs;

  if (!o.coverage_available) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
        <p className="font-medium text-gray-800 mb-1">No coverage available</p>
        <p className="text-sm text-gray-500">
          Google Solar data is not yet available for this address. Try again later.
        </p>
      </div>
    );
  }

  const roi   = calcROI(o.annual_kwh_estimate, o.max_panels);
  const grade = solarGrade(o.best_pitch_deg, o.best_azimuth_deg, o.sunshine_hours_per_year);

  return (
    <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">

      {/* Header */}
      <div className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-semibold text-gray-900">{report.address}</h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Run {report.run_date}
              {o.imagery_date !== 'unknown' && ` · Imagery ${o.imagery_date}`}
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {o.is_heritage && (
              <span className="text-xs font-medium px-2 py-1 bg-amber-100 text-amber-800 rounded-full">
                Heritage area
              </span>
            )}
            {/* Suitability grade badge */}
            <span className={`text-2xl font-bold px-3 py-1 rounded-lg ${grade.colour}`}>
              {grade.grade}
            </span>
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-2">{grade.reason} · {roi.systemKw.toFixed(1)} kW system</p>
      </div>

      {/* Aerial tile */}
      <div className="overflow-hidden">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={aerialTileUrl(report.lat, report.lng)}
          alt={`Satellite view of ${report.address}`}
          className="w-full object-cover"
          style={{ maxHeight: 220 }}
          onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
        />
      </div>

      {/* Financial ROI */}
      <div className="p-6">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-4">Financial return</h3>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <p className="text-xs text-gray-400 mb-0.5">Annual savings</p>
            <p className="text-xl font-semibold text-gray-900">{fmt$(roi.annualSaving)}</p>
            <p className="text-xs text-gray-400 mt-0.5">at current NSW rates</p>
          </div>
          <div>
            <p className="text-xs text-gray-400 mb-0.5">Payback period</p>
            <p className="text-xl font-semibold text-gray-900">
              {roi.paybackYears ? `${roi.paybackYears.toFixed(1)} yrs` : '—'}
            </p>
            <p className="text-xs text-gray-400 mt-0.5">system cost {fmt$(roi.systemCost)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-400 mb-0.5">10-year return</p>
            <p className={`text-xl font-semibold ${roi.tenYearReturn >= 0 ? 'text-emerald-700' : 'text-red-600'}`}>
              {fmt$(roi.tenYearReturn)}
            </p>
            <p className="text-xs text-gray-400 mt-0.5">after install + inverter</p>
          </div>
        </div>
        <p className="text-xs text-gray-400 mt-4 leading-relaxed">
          Assumes {fmt$(RETAIL_RATE * 100)}¢/kWh retail (AER DMO 2025–26 mid-market) · {fmt$(FEED_IN_RATE * 100)}¢/kWh
          feed-in (AER benchmark) · 30% self-consumption (ARENA/CSIRO Solar Home study) ·{' '}
          {fmt$(COST_PER_WATT * 1000)}/kW installed after STCs (SolarQuotes NSW 2026) · inverter
          replacement {fmt$(INVERTER_REPLACE)} at year 10.
        </p>
      </div>

      {/* Roof and system */}
      <div className="p-6">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-4">Roof and system</h3>
        <div className="grid grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-xs text-gray-400 mb-0.5">Max panels</p>
            <p className="font-medium text-gray-800">{o.max_panels} panels</p>
            <p className="text-xs text-gray-400">{roi.systemKw.toFixed(1)} kW</p>
          </div>
          <div>
            <p className="text-xs text-gray-400 mb-0.5">Usable roof area</p>
            <p className="font-medium text-gray-800">{o.max_panel_area_m2} m²</p>
            <p className="text-xs text-gray-400">of {o.roof_area_m2} m² total</p>
          </div>
          <div>
            <p className="text-xs text-gray-400 mb-0.5">Best orientation</p>
            <p className="font-medium text-gray-800">{azimuthLabel(o.best_azimuth_deg)} · {o.best_pitch_deg}° pitch</p>
            <p className="text-xs text-gray-400">{o.sunshine_hours_per_year.toLocaleString()} hr/yr sun</p>
          </div>
          <div>
            <p className="text-xs text-gray-400 mb-0.5">Annual output</p>
            <p className="font-medium text-gray-800">{o.annual_kwh_estimate.toLocaleString()} kWh</p>
            <p className="text-xs text-gray-400">full roof potential</p>
          </div>
        </div>
      </div>

      {/* Heritage warning */}
      {o.is_heritage && (
        <div className="px-6 py-4 bg-amber-50 text-xs text-amber-800">
          Heritage area — solar panel installations may require council heritage approval before proceeding.
        </div>
      )}

      {/* Footer */}
      <div className="px-6 py-4">
        <p className="text-xs text-gray-400">
          Data: {report.data_sources.join(' · ')} · Google Maps Static API
        </p>
        <p className="text-xs text-gray-400 mt-0.5">
          Solar potential assessment only. Financial figures are indicative estimates, not financial advice.
          Actual savings depend on household consumption, tariff structure, and system performance.
          Not a substitute for a professional energy or financial assessment.
        </p>
      </div>
    </div>
  );
}

function Metric({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="p-6">
      <p className="text-xs text-gray-400 mb-1">{label}</p>
      <p className="text-xl font-semibold text-gray-900">{value}</p>
      <p className="text-xs text-gray-400 mt-1">{note}</p>
    </div>
  );
}
