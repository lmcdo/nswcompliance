'use client';

import { useState, useMemo, useEffect, useCallback } from 'react';
import dynamic from 'next/dynamic';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';
import { ToolCrossSell } from '@/components/reports/ToolCrossSell';
import { posthog } from '@/components/providers/PostHogProvider';

const ShadowMap = dynamic(
  () => import('@/components/reports/ShadowMap').then(m => m.ShadowMap),
  { ssr: false, loading: () => <div className="w-full h-full bg-gray-100 animate-pulse rounded" /> }
);

const AerialTile = dynamic(
  () => import('@/components/reports/AerialTile').then(m => m.AerialTile),
  { ssr: false, loading: () => <div className="w-full bg-gray-100 animate-pulse" style={{ height: 220 }} /> }
);

interface GeoJSONGeometry {
  type: string;
  coordinates: unknown[];
}

interface GeoJSONCollection {
  type: 'FeatureCollection';
  features: { type: 'Feature'; geometry: GeoJSONGeometry; properties?: Record<string, unknown> }[];
}

interface ShadowScenario {
  scenario: string;
  label: string;
  date: string;
  time_local: string;
  shadow_length_m: number;
  shadow_overlap_fraction: number;
  shadow_direction_deg: number;
  overlaps_subject_lot: boolean;
  shadow_on_lot: GeoJSONCollection | null;
  shadow_polygon: GeoJSONCollection | null;
}

interface ShadowOutputs {
  height_m: number;
  height_source: 'planning_portal' | 'spatial_overlays' | 'regulatory_provisions' | 'default' | null;
  lep_name: string | null;
  lot_polygon: GeoJSONGeometry | null;
  north_proxy_polygon: GeoJSONGeometry | null;
  scenarios: ShadowScenario[];
  construction_change_score: number | null;
  construction_change_detected: boolean;
  adg_compliant: boolean;
  worst_case_scenario: string;
}

interface ShadowResult {
  address: string;
  lat: number;
  lng: number;
  run_date: string;
  outputs: ShadowOutputs;
  confidence: string;
  data_sources: string[];
  zone: string | null;
  warnings?: string[];
  report_token?: string;
  report_id?: string;
}

type PageState = 'idle' | 'running' | 'complete' | 'error';

const NON_RESIDENTIAL_ZONE_PREFIXES = ['B', 'E', 'IN', 'SP', 'W'];

const SCENARIO_LABELS: Record<string, string> = {
  jun21_9am: '21 Jun — 9:00 am',
  jun21_12pm: '21 Jun — 12:00 pm',
  jun21_3pm: '21 Jun — 3:00 pm',
  sep21_12pm: '21 Sep — 12:00 pm',
  dec21_12pm: '21 Dec — 12:00 pm',
};

function formatAustralianDate(isoDate: string): string {
  const [year, month, day] = isoDate.split('-').map(Number);
  const d = new Date(year, month - 1, day);
  return d.toLocaleDateString('en-AU', { day: 'numeric', month: 'long', year: 'numeric' });
}

function bearingToCompass(deg: number): string {
  const dirs = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
  return dirs[Math.round(deg / 45) % 8];
}

export function ShadowTool({ lgaSlug, embedRef }: { lgaSlug?: string; embedRef?: string }) {
  const [address, setAddress] = useState('');
  const [state, setState] = useState<PageState>('idle');
  const [result, setResult] = useState<ShadowResult | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [unlocking, setUnlocking] = useState(false);
  const [unlockError, setUnlockError] = useState('');
  const [paidReportId, setPaidReportId] = useState<string | null>(null);

  const runCheck = useCallback(async (addr: string) => {
    if (!addr.trim()) return;
    setState('running');
    setResult(null);
    setErrorMsg('');

    posthog?.capture('shadow_tool_run', {
      address: addr,
      lga_slug: lgaSlug,
      source: embedRef ? 'embed' : lgaSlug ? 'lga_page' : 'direct',
      embed_ref: embedRef ?? null,
    });

    try {
      const res = await fetch('/api/satellite/shadow', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address: addr }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || 'Shadow analysis failed');
      setResult(json);
      setState('complete');
      posthog?.capture('shadow_tool_complete', {
        address: addr,
        lga_slug: lgaSlug,
        adg_compliant: json.outputs?.adg_compliant,
        confidence: json.confidence,
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setErrorMsg(msg);
      setState('error');
      posthog?.capture('shadow_tool_error', { address: addr, lga_slug: lgaSlug, error: msg });
    }
  }, [embedRef, lgaSlug]);

  useEffect(() => {
    const handler = (e: Event) => {
      const addr = (e as CustomEvent).detail?.address;
      if (addr) {
        setAddress(addr);
        runCheck(addr);
      }
    };
    window.addEventListener('landing-search', handler);
    return () => window.removeEventListener('landing-search', handler);
  }, [runCheck]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);

    const addrParam = params.get('address')?.trim();
    if (addrParam && !params.get('payment')) {
      setAddress(addrParam);
      runCheck(addrParam);
      window.history.replaceState({}, '', window.location.pathname);
    }

    if (params.get('payment') === 'success') {
      const rid = params.get('report_id')?.trim();
      if (rid) setPaidReportId(rid);
      window.history.replaceState({}, '', window.location.pathname);
    }
  }, [runCheck]);

  const handleUnlock = async (reportId: string, addr: string) => {
    setUnlocking(true);
    setUnlockError('');
    try {
      const res = await fetch('/api/stripe/checkout/shadow', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report_id: reportId, address: addr }),
      });
      const json = await res.json();
      if (!res.ok || !json.checkout_url) throw new Error(json.error || 'Checkout failed');
      window.location.href = json.checkout_url;
    } catch (err: unknown) {
      setUnlockError(err instanceof Error ? err.message : 'Something went wrong');
      setUnlocking(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    runCheck(address);
  };

  return (
    <div>
      <form id="tool-input" onSubmit={handleSubmit} className="flex gap-3 mb-8">
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
          {state === 'running' ? 'Analysing...' : 'Analyse'}
        </button>
      </form>

      {state === 'running' && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 flex flex-col items-center text-center">
          <div className="w-8 h-8 border-2 border-teal-600 border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-sm font-medium text-gray-700">Running shadow model across 5 ADG scenarios...</p>
          <p className="text-xs text-gray-400 mt-1">This takes 15–30 seconds.</p>
        </div>
      )}

      {state === 'error' && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-sm text-red-700">
          {errorMsg}
        </div>
      )}

      {paidReportId && state !== 'complete' && (
        <ShadowPaidDownloadCTA reportId={paidReportId} />
      )}

      {state === 'complete' && result && (
        <>
          <ShadowCard result={result} />
          {result.report_id ? (
            paidReportId ? (
              <ShadowPaidDownloadCTA reportId={paidReportId} />
            ) : (
              <ShadowLockedPreviewCard
                result={result}
                onUnlock={() => handleUnlock(result.report_id!, result.address)}
                unlocking={unlocking}
                error={unlockError}
              />
            )
          ) : null}
          <ToolCrossSell currentTool="shadow-detector" address={result.address} />
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ShadowLockedPreviewCard — gate documentation value, not the verdict
// Free: ADG verdict + map. Paid: scenario data, construction detection, objection para.
// ---------------------------------------------------------------------------

const SCENARIO_ORDER = ['jun21_9am', 'jun21_12pm', 'jun21_3pm', 'sep21_12pm', 'dec21_12pm'];

function ShadowLockedPreviewCard({
  result,
  onUnlock,
  unlocking,
  error,
}: {
  result: ShadowResult;
  onUnlock: () => void;
  unlocking: boolean;
  error: string;
}) {
  const o = result.outputs;
  const overlapCount = o.scenarios.filter(s => s.overlaps_subject_lot).length;

  // Find worst-case overlap fraction for blurred preview
  const worstScenario = o.scenarios.find(s => s.scenario === o.worst_case_scenario);
  const worstOverlapPct = worstScenario?.shadow_overlap_fraction != null
    ? `${Math.round(worstScenario.shadow_overlap_fraction * 100)}% of lot`
    : `${overlapCount} of 5 scenarios`;

  // Sort scenarios in standard order for consistent display
  const sortedScenarios = [...o.scenarios].sort(
    (a, b) => SCENARIO_ORDER.indexOf(a.scenario) - SCENARIO_ORDER.indexOf(b.scenario)
  );
  const teaserScenarios = sortedScenarios.slice(0, 2);
  const blurredCount = Math.max(0, sortedScenarios.length - 2);

  const alarmHeadline = !o.adg_compliant
    ? `ADG concern — shadow impact on ${overlapCount} of 5 test scenarios`
    : overlapCount > 0
    ? `Shadow impact on ${overlapCount} of 5 scenarios — get the diagrams for your records`
    : 'Shadow analysis complete — get the council-ready documentation';

  const alarmDetail = !o.adg_compliant
    ? 'This property may not meet the ADG 2-hour solar access requirement on 21 June. The full report has the scenario diagrams and objection paragraph you need.'
    : 'The full report includes hourly shadow diagrams and a ready-to-paste objection paragraph for your council submission.';

  return (
    <div className="mt-4 rounded-xl border border-gray-200 overflow-hidden">
      <div className="bg-amber-50 border-b border-amber-100 px-5 py-4">
        <p className="text-sm font-semibold text-amber-900 leading-snug">{alarmHeadline}</p>
        <p className="text-xs text-amber-700 mt-1 leading-relaxed">{alarmDetail}</p>
      </div>

      <div className="bg-white px-5 pt-4 pb-3 space-y-4">
        {/* Construction detection — blurred */}
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
            Construction detected nearby
          </p>
          <span className="blur-sm select-none pointer-events-none text-sm font-medium text-gray-900">
            {o.construction_change_detected ? 'Yes — recent activity detected' : 'No recent construction activity'}
          </span>
        </div>

        {/* Worst-case overlap — blurred */}
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
            Shadow overlap — worst case
          </p>
          <span className="blur-sm select-none pointer-events-none text-sm font-medium text-gray-900">
            {worstOverlapPct}
          </span>
        </div>

        {/* Scenario table — 2 teasers + blurred rows */}
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
            Scenario breakdown
          </p>
          <div className="space-y-1.5">
            {teaserScenarios.map((s) => (
              <div key={s.scenario} className="flex items-center justify-between gap-4 text-sm py-1 border-b border-gray-50">
                <span className="text-gray-600">{SCENARIO_LABELS[s.scenario] ?? s.scenario}</span>
                <span className="font-medium text-gray-900 tabular-nums">
                  {s.shadow_length_m.toFixed(0)}m shadow
                  {s.overlaps_subject_lot ? ' · overlaps lot' : ''}
                </span>
              </div>
            ))}
            {/* Blurred remaining rows */}
            {Array.from({ length: blurredCount }).map((_, i) => (
              <div key={`blur-${i}`} className="flex items-center justify-between gap-4 text-sm py-1 border-b border-gray-50">
                <span className="blur-sm select-none pointer-events-none text-gray-600">
                  {SCENARIO_LABELS[SCENARIO_ORDER[2 + i]] ?? `Scenario ${3 + i}`}
                </span>
                <span className="blur-sm select-none pointer-events-none font-medium text-gray-900 tabular-nums">
                  {14 + i * 3}m shadow · {i === 0 ? 'overlaps lot' : 'clear'}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Objection paragraph — fully blurred block */}
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
            Objection-ready paragraph
          </p>
          <p className="blur-sm select-none pointer-events-none text-sm text-gray-700 leading-relaxed">
            Shadow modelling conducted in accordance with NSW Apartment Design Guide Part 3F
            indicates that a maximum-height building on the northern boundary would cast a shadow
            over {Math.round((worstScenario?.shadow_overlap_fraction ?? 0.3) * 100)}% of the subject
            lot at 21 June 12pm, which does not comply with the 2-hour solar access requirement.
          </p>
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
            'Unlock shadow report — $29'
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
// ShadowPaidDownloadCTA — shown after Stripe payment=success redirect
// ---------------------------------------------------------------------------

function ShadowPaidDownloadCTA({ reportId }: { reportId: string }) {
  const [downloading, setDownloading] = useState(false);
  const [dlError, setDlError] = useState('');

  const handleDownload = async () => {
    setDownloading(true);
    setDlError('');
    try {
      const res = await fetch('/api/reports/shadow/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report_id: reportId }),
      });
      if (!res.ok) throw new Error('PDF generation failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `shadow-report-${reportId.slice(0, 8)}.pdf`;
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

function ShadowCard({ result }: { result: ShadowResult }) {
  const o = result.outputs;
  const scenarios = o.scenarios ?? [];

  const [activeScenario, setActiveScenario] = useState<string>(
    o.worst_case_scenario ?? 'jun21_12pm'
  );

  const activeShadowOnLot = useMemo(() => {
    const match = scenarios.find(s => s.scenario === activeScenario);
    return match?.shadow_on_lot ?? null;
  }, [activeScenario, scenarios]);

  const overlapCount = scenarios.filter(s => s.overlaps_subject_lot).length;

  const isNonResidential =
    result.zone != null &&
    NON_RESIDENTIAL_ZONE_PREFIXES.some(p => result.zone!.toUpperCase().startsWith(p));

  const adgColor = isNonResidential
    ? 'text-gray-600 bg-gray-100'
    : o.adg_compliant
    ? 'text-green-700 bg-green-100'
    : 'text-red-700 bg-red-100';

  const adgLabel = isNonResidential
    ? 'ADG — indicative only'
    : o.adg_compliant
    ? 'ADG compliant'
    : 'ADG concern';

  const summaryText = isNonResidential
    ? overlapCount === 0
      ? `A maximum-height building on an adjacent lot would not significantly shadow this property across any of the 5 test scenarios. ADG solar access requirements apply to residential apartment buildings only — this result is indicative.`
      : `A maximum-height building on an adjacent lot would significantly shadow this property on ${overlapCount} of 5 scenarios. ADG solar access requirements apply to residential apartment buildings only — this result is indicative.`
    : o.adg_compliant
    ? overlapCount === 0
      ? `A maximum-height building on an adjacent lot would not significantly shadow this property across any of the 5 test scenarios. ADG solar access requirements are met.`
      : `A maximum-height building on an adjacent lot would significantly shadow this property on ${overlapCount} of 5 scenarios, but still meets ADG solar access requirements (2 hours between 9 am–3 pm on 21 June).`
    : `A maximum-height building on an adjacent lot would significantly shadow this property on ${overlapCount} of 5 scenarios and may not meet the ADG 2-hour solar access requirement on 21 June.`;

  return (
    <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">

      {/* Header */}
      <div className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-semibold text-gray-900">{result.address}</h2>
            <p className="text-xs text-gray-400 mt-0.5">Run {result.run_date ? formatAustralianDate(result.run_date) : ''}</p>
          </div>
          <span className={`shrink-0 text-xs font-medium px-2 py-1 rounded-full ${adgColor}`}>
            {adgLabel}
          </span>
        </div>
        <p className="text-sm text-gray-600 mt-3 leading-relaxed">{summaryText}</p>
      </div>

      {/* Map */}
      <div className="relative" style={{ height: 280 }}>
        <ShadowMap
          center={[result.lng, result.lat]}
          lotPolygon={o.lot_polygon ?? null}
          shadowOnLot={activeShadowOnLot}
        />
        {/* North arrow */}
        <div className="absolute bottom-3 left-3 bg-black/60 text-white rounded-full w-8 h-8 flex flex-col items-center justify-center gap-0 select-none">
          <svg width="10" height="12" viewBox="0 0 10 12" fill="none">
            <path d="M5 1 L5 11" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
            <path d="M5 1 L2 5 M5 1 L8 5" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
          <span className="text-[9px] font-bold leading-none">N</span>
        </div>

        {/* Scenario label overlay */}
        <div className="absolute bottom-3 left-12 bg-black/60 text-white text-xs px-2.5 py-1 rounded-full">
          {SCENARIO_LABELS[activeScenario] ?? activeScenario}
        </div>
        {/* Legend */}
        <div className="absolute top-3 right-3 bg-white/90 text-xs rounded-lg px-3 py-2 space-y-1.5 shadow-sm">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-sm bg-teal-500 opacity-70 shrink-0" />
            <span className="text-gray-700">Subject lot</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-sm bg-orange-400 opacity-80 shrink-0" />
            <span className="text-gray-700">Shadow on lot</span>
          </div>
        </div>
      </div>
      <p className="px-6 py-2 text-xs text-gray-400 border-b border-gray-100">
        Shadow modelled from the north lot boundary at max permitted height. Geometric model — not derived from satellite imagery. Aerial imagery © Esri.
      </p>

      {/* Aerial satellite view with lot boundary */}
      {o.lot_polygon && o.lot_polygon.type === 'Polygon' && (
        <div style={{ height: 220 }}>
          <AerialTile lat={result.lat} lng={result.lng} lotPolygon={o.lot_polygon as { type: 'Polygon'; coordinates: number[][][] }} />
        </div>
      )}

      {/* Warnings */}
      {result.warnings && result.warnings.length > 0 && (
        <div className="px-6 py-4 bg-amber-50 space-y-1">
          {result.warnings.map((w, i) => (
            <p key={i} className="text-xs text-amber-800">{w}</p>
          ))}
        </div>
      )}

      {/* Methodology */}
      <details className="group">
        <summary className="px-6 py-4 cursor-pointer list-none flex items-center justify-between text-xs text-gray-400 hover:text-gray-600 transition-colors">
          <span>How this is calculated</span>
          <span className="group-open:rotate-180 transition-transform">▾</span>
        </summary>
        <div className="px-6 pb-5 space-y-2 text-xs text-gray-500 leading-relaxed border-t border-gray-50">
          <p>
            <span className="font-medium text-gray-600">Authority.</span>{' '}
            Test dates and times follow the NSW Apartment Design Guide (Department of Planning, Housing and Infrastructure, 2015),
            Part 3F — Solar and Daylight Access. The critical test is 21 June (winter solstice), when shadows are longest.
          </p>
          <p>
            <span className="font-medium text-gray-600">Solar position.</span>{' '}
            Sun azimuth and altitude are calculated using the NREL Solar Position Algorithm
            (Reda &amp; Andreas, 2004) — the international standard used by solar engineers and
            shadow consultants. Verified for Sydney&apos;s latitude (Southern Hemisphere).
          </p>
          <p>
            <span className="font-medium text-gray-600">Building height and footprint.</span>{' '}
            The model assumes the maximum permissible building height under the applicable
            Local Environmental Plan (LEP). The northern neighbour&apos;s footprint is
            approximated using the subject lot&apos;s own cadastral boundary, offset one
            lot-depth northward — a conservative symmetric proxy for suburban and terrace
            lots. Where a road lies to the north, the actual nearest building would be
            further away, meaning real shadow impact would be less than modelled.
            Actual development may be smaller or differently positioned.
          </p>
          <p>
            <span className="font-medium text-gray-600">Construction activity.</span>{' '}
            Detected using the Bare Soil Index (BSI) — a spectral formula applied to
            Sentinel-2 satellite imagery that measures exposed bare earth. A change score
            above 0.120 between recent scenes (&lt;90 days) and a 12-month baseline indicates
            likely demolition, excavation, or site clearing.
          </p>
          <p>
            <span className="font-medium text-gray-600">Limitation.</span>{' '}
            This is a worst-case envelope model, not a design-specific assessment.
            A formal shadow impact assessment prepared by a qualified town planner or
            architect is required for Development Application (DA) submission.
          </p>
          <p className="text-gray-400">
            Data sources: {(result.data_sources ?? []).join(' · ')}
          </p>
        </div>
      </details>
    </div>
  );
}
