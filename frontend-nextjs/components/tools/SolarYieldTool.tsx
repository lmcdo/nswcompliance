'use client';

import { useState, useEffect, useRef } from 'react';
import dynamic from 'next/dynamic';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';
import { ToolCrossSell } from '@/components/reports/ToolCrossSell';
import { posthog } from '@/components/providers/PostHogProvider';

const AerialTile = dynamic(
  () => import('@/components/reports/AerialTile').then(m => m.AerialTile),
  { ssr: false, loading: () => <div className="w-full bg-gray-100 animate-pulse" style={{ height: 220 }} /> }
);

interface SolarYieldOutputs {
  max_panels: number;
  max_panel_area_m2: number;
  annual_kwh_estimate: number;
  sunshine_hours_per_year: number;
  best_pitch_deg: number;
  best_azimuth_deg: number;
  roof_area_m2: number;
  is_heritage: boolean;
  is_commercial_scale: boolean;
  imagery_date: string;
  coverage_available: boolean;
}

interface GeoJSONPolygon {
  type: 'Polygon';
  coordinates: number[][][];
}

interface ReportData {
  product: string;
  address: string;
  lat: number;
  lng: number;
  lot_polygon: GeoJSONPolygon | null;
  run_date: string;
  outputs: SolarYieldOutputs;
  confidence: string;
  data_sources: string[];
  report_token?: string;
  report_id?: string;
}

type PageState = 'idle' | 'running' | 'complete' | 'error' | 'ineligible';

const PANEL_WATTS        = 400;
const RETAIL_RATE        = 0.32;   // $/kWh — matches solar-yield generate route
const FEED_IN_TARIFF     = 0.06;   // $/kWh
const SELF_CONSUME_RATIO = 0.30;
const COST_PER_WATT      = 1.00;   // $/W installed

function solarGrade(pitch: number, azimuth: number, sunshineHours: number): {
  grade: string; colour: string; reason: string;
  pitchLabel: string; azLabel: string; sunLabel: string;
} {
  const pitchScore =
    pitch >= 15 && pitch <= 30 ? 3 :
    pitch >= 8  && pitch < 15  ? 2 :
    pitch >= 30 && pitch <= 40 ? 2 : 1;

  const pitchLabel =
    pitchScore === 3 ? 'ideal' :
    pitchScore === 2 ? 'acceptable' : 'flat/steep';

  const northDev = Math.min(azimuth, 360 - azimuth);
  const azScore =
    northDev <= 30  ? 3 :
    northDev <= 60  ? 2 :
    northDev <= 90  ? 1 : 0;

  const azLabel =
    azScore === 3 ? 'north-facing' :
    azScore === 2 ? 'partial north' :
    azScore === 1 ? 'east/west'    : 'south-facing';

  const sunScore =
    sunshineHours >= 1700 ? 3 :
    sunshineHours >= 1500 ? 2 :
    sunshineHours >= 1300 ? 1 : 0;

  const sunLabel =
    sunScore === 3 ? 'high' :
    sunScore === 2 ? 'good' :
    sunScore === 1 ? 'moderate' : 'low';

  const total = pitchScore + azScore + sunScore;

  if (total >= 8) return { grade: 'A', colour: 'text-emerald-700 bg-emerald-50', reason: 'Excellent solar potential', pitchLabel, azLabel, sunLabel };
  if (total >= 6) return { grade: 'B', colour: 'text-teal-700 bg-teal-50',       reason: 'Good solar potential',      pitchLabel, azLabel, sunLabel };
  if (total >= 4) return { grade: 'C', colour: 'text-yellow-700 bg-yellow-50',   reason: 'Moderate solar potential',  pitchLabel, azLabel, sunLabel };
  if (total >= 2) return { grade: 'D', colour: 'text-orange-700 bg-orange-50',   reason: 'Below-average solar potential', pitchLabel, azLabel, sunLabel };
  return           { grade: 'F', colour: 'text-red-700 bg-red-50',               reason: 'Poor solar potential',      pitchLabel, azLabel, sunLabel };
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

export function SolarYieldTool({ lgaSlug, embedRef }: { lgaSlug?: string; embedRef?: string }) {
  const [address, setAddress] = useState('');
  const [inputAddress, setInputAddress] = useState('');
  const [state, setState] = useState<PageState>('idle');
  const [report, setReport] = useState<ReportData | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [ineligible, setIneligible] = useState<{ error: string; evidence?: string; evidence_label?: string } | null>(null);
  const [unlocking, setUnlocking] = useState(false);
  const [unlockError, setUnlockError] = useState('');
  const [paidReportId, setPaidReportId] = useState<string | null>(null);
  const formRef = useRef<HTMLFormElement>(null);

  // Listen for hero address input — submit directly after state update flushes
  useEffect(() => {
    const handler = (e: Event) => {
      const addr = (e as CustomEvent).detail?.address;
      if (addr) {
        setAddress(addr);
        setTimeout(() => formRef.current?.requestSubmit(), 0);
      }
    };
    window.addEventListener('landing-search', handler);
    return () => window.removeEventListener('landing-search', handler);
  }, []);

  // Read URL params on mount: ?address= (auto-run) and ?payment=success (download CTA)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);

    const addrParam = params.get('address')?.trim();
    if (addrParam && !params.get('payment')) {
      setAddress(addrParam);
      setTimeout(() => formRef.current?.requestSubmit(), 0);
      window.history.replaceState({}, '', window.location.pathname);
    }

    if (params.get('payment') === 'success') {
      const rid = params.get('report_id')?.trim();
      if (rid) setPaidReportId(rid);
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, []);

  const handleUnlock = async () => {
    if (!report?.report_id || !report?.address) return;
    setUnlocking(true);
    setUnlockError('');
    try {
      const res = await fetch('/api/stripe/checkout/solar-yield', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report_id: report.report_id, address: report.address }),
      });
      const json = await res.json();
      if (!res.ok || !json.checkout_url) throw new Error(json.error || 'Checkout failed');
      window.location.href = json.checkout_url;
    } catch (err: unknown) {
      setUnlockError(err instanceof Error ? err.message : 'Something went wrong');
      setUnlocking(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!address.trim()) return;

    setInputAddress(address.trim());
    setState('running');
    setReport(null);
    setErrorMsg('');
    setIneligible(null);

    try {
      const res = await fetch('/api/satellite/solar-yield', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address }),
      });

      const json = await res.json();

      if (!res.ok) {
        if (json.ineligible) {
          setIneligible({ error: json.error, evidence: json.evidence, evidence_label: json.evidence_label });
          setState('ineligible');
          return;
        }
        throw new Error(json.error || 'Failed to run report');
      }

      setReport(json.data);
      setState('complete');
      posthog.capture('tool_run', {
        tool: 'solar-yield',
        source: embedRef ? 'embed' : lgaSlug ? 'lga_page' : 'direct',
        embed_ref: embedRef ?? null,
        lga_slug: lgaSlug ?? null,
        result: json.data?.outputs?.coverage_available ? 'coverage_available' : 'no_coverage',
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setErrorMsg(msg);
      setState('error');
    }
  };

  return (
    <div className="mb-8">
      <form ref={formRef} id="tool-input" onSubmit={handleSubmit} className="flex gap-3 mb-8">
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

      {state === 'ineligible' && ineligible && (
        <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
          <div className="p-6 flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-gray-900">{inputAddress}</p>
              <button
                type="button"
                onClick={() => { setState('idle'); setIneligible(null); setAddress(''); }}
                className="text-xs text-teal-600 hover:text-teal-700 underline mt-1"
              >
                Check another address
              </button>
            </div>
            <span className="shrink-0 text-xs font-medium px-2 py-1 rounded-full bg-amber-100 text-amber-800">
              Not assessable
            </span>
          </div>
          <div className="p-6">
            <p className="text-sm text-gray-700">{ineligible.error}</p>
          </div>
          {ineligible.evidence && (
            <div className="px-6 py-3 bg-gray-50">
              <p className="text-xs text-gray-400 mb-0.5">{ineligible.evidence_label || 'Source'}</p>
              <p className="text-xs font-mono text-gray-600">{ineligible.evidence}</p>
            </div>
          )}
        </div>
      )}

      {/* Payment return — show download CTA even without report in state */}
      {paidReportId && state !== 'complete' && (
        <PaidDownloadCTA reportId={paidReportId} />
      )}

      {state === 'complete' && report && (
        <>
          <ReportCard report={report} />
          {report.outputs.coverage_available && report.report_id ? (
            paidReportId ? (
              <PaidDownloadCTA reportId={paidReportId} />
            ) : (
              <SolarLockedPreviewCard
                outputs={report.outputs}
                onUnlock={handleUnlock}
                unlocking={unlocking}
                error={unlockError}
              />
            )
          ) : null}
          <ToolCrossSell currentTool="solar-yield" address={report.address} />
        </>
      )}
    </div>
  );
}

function ReportCard({ report }: { report: ReportData }) {
  const o = report.outputs;

  if (!o.coverage_available) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
        <div className="p-6">
          <h2 className="font-semibold text-gray-900">{report.address}</h2>
          <p className="text-xs text-gray-400 mt-0.5">Run {report.run_date}</p>
        </div>
        <div className="p-6">
          <p className="text-sm font-medium text-gray-700 mb-1">Building data not available for this address</p>
          <p className="text-sm text-gray-500 leading-relaxed">
            Google Solar building data covers Sydney metro and major NSW cities.
            Precise roof area, panel count, and yield figures aren&apos;t available here yet.
          </p>
        </div>
        <CoverageInterestForm address={report.address} lat={report.lat} lng={report.lng} />
      </div>
    );
  }

  const systemKw = (o.max_panels * PANEL_WATTS) / 1000;
  const grade    = solarGrade(o.best_pitch_deg, o.best_azimuth_deg, o.sunshine_hours_per_year);

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
            <div className={`flex flex-col items-center px-3 py-2 rounded-lg ${grade.colour}`}>
              <span className="text-[10px] font-semibold uppercase tracking-wide opacity-60 leading-none mb-1">Suitability</span>
              <span className="text-xl font-bold leading-none">{grade.grade}</span>
            </div>
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          {grade.reason} · {systemKw.toFixed(1)} kW system
        </p>
        <p className="text-xs text-gray-400 mt-1">
          Pitch {o.best_pitch_deg}° ({grade.pitchLabel}) · Orientation {azimuthLabel(o.best_azimuth_deg)} ({grade.azLabel}) · Sunshine {o.sunshine_hours_per_year.toLocaleString('en-AU')} hr/yr ({grade.sunLabel}) · A = excellent · B = good · C = moderate · D = below average · F = poor.
        </p>
      </div>

      {/* Aerial tile */}
      <div style={{ height: 220 }}>
        <AerialTile lat={report.lat} lng={report.lng} lotPolygon={o.coverage_available ? report.lot_polygon : null} />
      </div>

      {/* Free tier summary — orientation + kWh only, no $ figures */}
      <div className="p-6">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-xs text-gray-400 mb-0.5">Best orientation</p>
            <p className="font-medium text-gray-800">{azimuthLabel(o.best_azimuth_deg)} · {o.best_pitch_deg}° pitch</p>
            <p className="text-xs text-gray-400">{o.sunshine_hours_per_year.toLocaleString('en-AU')} hr/yr sun</p>
          </div>
          <div>
            <p className="text-xs text-gray-400 mb-0.5">Annual output estimate</p>
            <p className="font-medium text-gray-800">{Math.round(o.annual_kwh_estimate).toLocaleString('en-AU')} kWh/yr</p>
            <p className="text-xs text-gray-400">full roof potential</p>
          </div>
        </div>
      </div>

      {/* Commercial scale notice */}
      {o.is_commercial_scale && (
        <div className="px-6 py-4 bg-sky-50 text-xs text-sky-800">
          Large-scale roof detected ({o.roof_area_m2.toLocaleString('en-AU')} m²). Results reflect
          panels within this lot boundary only. A commercial energy assessment is recommended
          for multi-tenancy or strata sites.
        </div>
      )}

      {/* Heritage warning */}
      {o.is_heritage && (
        <div className="px-6 py-4 bg-amber-50 text-xs text-amber-800 space-y-1">
          <p className="font-medium">Heritage item or conservation area</p>
          <p>
            Solar panels visible from a public place on a heritage item or within a Heritage Conservation Area
            may require council approval under your LEP (cl 5.10). Panels on rear or concealed roof faces
            are generally approvable — panels on the street-facing primary facade are often refused.
            Confirm with council or a heritage consultant before proceeding.
          </p>
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

function CoverageInterestForm({ address, lat, lng }: { address: string; lat: number; lng: number }) {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'submitting' | 'done' | 'error'>('idle');
  const [suburb, setSuburb] = useState('your area');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    setStatus('submitting');
    try {
      const res = await fetch('/api/satellite/solar-coverage-interest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, address, lat, lng }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error);
      if (json.suburb) setSuburb(json.suburb);
      setStatus('done');
    } catch {
      setStatus('error');
    }
  };

  if (status === 'done') {
    return (
      <div className="px-6 py-5 bg-teal-50">
        <p className="text-sm font-medium text-teal-800">You&apos;re on the list.</p>
        <p className="text-xs text-teal-700 mt-0.5">
          We&apos;ll email you when full roof analysis reaches {suburb}.
        </p>
      </div>
    );
  }

  return (
    <div className="px-6 py-5 bg-gray-50">
      <p className="text-sm font-medium text-gray-700 mb-0.5">
        Get notified when we expand to {address.match(/,\s*([^,]+?)\s+NSW/i)?.[1] ?? 'your area'}
      </p>
      <p className="text-xs text-gray-500 mb-3">
        We&apos;re rolling out building-level analysis across NSW. One email when it&apos;s ready — no spam.
      </p>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          placeholder="your@email.com"
          disabled={status === 'submitting'}
          className="flex-1 px-3 py-2 text-sm rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent disabled:opacity-50"
          required
        />
        <button
          type="submit"
          disabled={status === 'submitting' || !email.trim()}
          className="px-4 py-2 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
        >
          {status === 'submitting' ? 'Saving...' : 'Notify me'}
        </button>
      </form>
      {status === 'error' && (
        <p className="text-xs text-red-600 mt-1">Something went wrong. Please try again.</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// SolarLockedPreviewCard — blur-to-reveal with real computed financial values
// ---------------------------------------------------------------------------

function SolarLockedPreviewCard({
  outputs,
  onUnlock,
  unlocking,
  error,
}: {
  outputs: SolarYieldOutputs;
  onUnlock: () => void;
  unlocking: boolean;
  error: string;
}) {
  const systemKw        = (outputs.max_panels * PANEL_WATTS) / 1000;
  const annualKwh       = outputs.annual_kwh_estimate;
  const selfConsumed    = annualKwh * SELF_CONSUME_RATIO;
  const exported        = annualKwh * (1 - SELF_CONSUME_RATIO);
  const annualSavings   = (selfConsumed * RETAIL_RATE) + (exported * FEED_IN_TARIFF);
  const systemCost      = systemKw * 1000 * COST_PER_WATT;
  const paybackYears    = systemCost / annualSavings;

  const fmt = (n: number, prefix = '') =>
    prefix + Math.round(n).toLocaleString('en-AU');

  const rows = [
    { label: 'Annual electricity savings',  preview: `$${fmt(annualSavings)} / yr` },
    { label: 'Payback period',              preview: `${paybackYears.toFixed(1)} years` },
    { label: `System size — ${systemKw.toFixed(1)} kW`, preview: `${outputs.max_panels} panels` },
    { label: 'Installed cost estimate',     preview: `$${fmt(systemCost)}` },
    { label: 'Feed-in contribution',        preview: `$${fmt(exported * FEED_IN_TARIFF)} / yr` },
    { label: 'Full PDF report',             preview: 'solar-yield-report.pdf' },
  ];

  return (
    <div className="mt-4 rounded-xl border border-gray-200 overflow-hidden">
      <div className="bg-amber-50 border-b border-amber-100 px-5 py-4">
        <p className="text-sm font-semibold text-amber-900 leading-snug">
          {fmt(outputs.annual_kwh_estimate)} kWh / yr potential — see the full financial case
        </p>
        <p className="text-xs text-amber-700 mt-1 leading-relaxed">
          Your installer will ask for panel count, system size, and payback period before quoting.
          Your numbers are below — unlocked with one payment.
        </p>
      </div>

      <div className="bg-white px-5 pt-4 pb-3">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3">
          Your solar financials
        </p>
        <div className="space-y-2">
          {rows.map(({ label, preview }) => (
            <div key={label} className="flex items-center justify-between gap-4 text-sm">
              <span className="text-gray-700">{label}</span>
              <span className="blur-sm select-none pointer-events-none font-medium text-gray-900 tabular-nums">
                {preview}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white px-5 pb-5 pt-2">
        <button
          onClick={onUnlock}
          disabled={unlocking}
          className="w-full py-2.5 px-4 bg-teal-600 text-white text-sm font-semibold rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
        >
          {unlocking ? (
            <>
              <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Starting checkout...
            </>
          ) : (
            'Unlock full analysis — $19'
          )}
        </button>
        {error && <p className="text-xs text-red-600 mt-2">{error}</p>}
        <p className="text-xs text-gray-400 text-center mt-2">
          Paid once. PDF delivered to your email after checkout.
        </p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// PaidDownloadCTA — shown after Stripe redirects back with payment=success
// ---------------------------------------------------------------------------

function PaidDownloadCTA({ reportId }: { reportId: string }) {
  const [downloading, setDownloading] = useState(false);
  const [dlError, setDlError] = useState('');

  const handleDownload = async () => {
    setDownloading(true);
    setDlError('');
    try {
      const res = await fetch('/api/reports/solar-yield/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report_id: reportId }),
      });
      if (!res.ok) throw new Error('PDF generation failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `solar-yield-report-${reportId.slice(0, 8)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      setDlError(err instanceof Error ? err.message : 'Download failed');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="mt-4 rounded-xl border border-teal-200 bg-teal-50 p-5">
      <p className="text-sm font-semibold text-teal-900 mb-1">Payment confirmed — your report is ready.</p>
      <p className="text-xs text-teal-700 mb-3">A copy is also on its way to your email.</p>
      <button
        onClick={handleDownload}
        disabled={downloading}
        className="w-full py-2.5 bg-teal-600 text-white text-sm font-semibold rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {downloading ? 'Preparing download...' : 'Download PDF report →'}
      </button>
      {dlError && <p className="text-xs text-red-600 mt-2">{dlError}</p>}
    </div>
  );
}
