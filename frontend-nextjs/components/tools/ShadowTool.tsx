'use client';

import { useState, useMemo } from 'react';
import dynamic from 'next/dynamic';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';
import { posthog } from '@/components/providers/PostHogProvider';

const ShadowMap = dynamic(
  () => import('@/components/reports/ShadowMap').then(m => m.ShadowMap),
  { ssr: false, loading: () => <div className="w-full h-full bg-gray-100 animate-pulse rounded" /> }
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

export function ShadowTool({ lgaSlug }: { lgaSlug?: string }) {
  const [address, setAddress] = useState('');
  const [state, setState] = useState<PageState>('idle');
  const [result, setResult] = useState<ShadowResult | null>(null);
  const [errorMsg, setErrorMsg] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!address.trim()) return;

    setState('running');
    setResult(null);
    setErrorMsg('');

    posthog?.capture('shadow_tool_run', { address, lga_slug: lgaSlug });

    try {
      const res = await fetch('/api/satellite/shadow', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address }),
      });

      const json = await res.json();

      if (!res.ok) {
        throw new Error(json.error || 'Shadow analysis failed');
      }

      setResult(json);
      setState('complete');
      posthog?.capture('shadow_tool_complete', {
        address,
        lga_slug: lgaSlug,
        adg_compliant: json.outputs?.adg_compliant,
        confidence: json.confidence,
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setErrorMsg(msg);
      setState('error');
      posthog?.capture('shadow_tool_error', { address, lga_slug: lgaSlug, error: msg });
    }
  };

  return (
    <div className="max-w-2xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Construction Shadow Detector</h1>
        <p className="mt-1.5 text-sm text-gray-500">
          Models the shadow a maximum-height building on an adjacent lot could cast across
          five key dates. Under the Apartment Design Guide (ADG), neighbouring properties
          must receive at least 2 hours of direct sunlight between 9 am and 3 pm on
          21 June (winter solstice).
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

      {state === 'complete' && result && <ShadowCard result={result} />}
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

      {/* Stats row */}
      <div className="grid grid-cols-2 divide-x divide-gray-100">
        <div className="p-6">
          <p className="text-xs text-gray-400 mb-1">Max building height modelled</p>
          <p className="text-xl font-semibold text-gray-900">{o.height_m} m</p>
          <p className="text-xs text-gray-400 mt-1">{o.lep_name ?? 'Local Environmental Plan'}</p>
          {o.height_source === 'default' && (
            <p className="text-xs text-amber-600 mt-1">
              No Height of Buildings control found in LEP — 9 m default used. Actual height limit may differ.
            </p>
          )}
        </div>
        <div className="p-6">
          <p className="text-xs text-gray-400 mb-1">Recent construction activity</p>
          <p className="text-xl font-semibold text-gray-900">
            {o.construction_change_detected ? 'Detected' : 'None detected'}
          </p>
          <p className="text-xs text-gray-400 mt-1">
            {o.construction_change_score != null
              ? o.construction_change_detected
                ? `Significant change detected — demolition or excavation visible in satellite imagery over the past 90 days. (BSI Δ ${o.construction_change_score.toFixed(3)}, threshold 0.120)`
                : `No significant change detected — no demolition or excavation visible in satellite imagery over the past 90 days. (BSI Δ ${o.construction_change_score.toFixed(3)}, threshold 0.120)`
              : 'Sentinel-2 satellite imagery analysed — past 90 days vs 12-month baseline'}
          </p>
        </div>
      </div>

      {/* Scenarios table — clicking a row switches the map */}
      <div className="p-6">
        <p className="text-sm font-medium text-gray-700 mb-1">Shadow impact by scenario</p>
        <p className="text-xs text-gray-400 mb-4">
          Click a row to view that shadow on the map. Does the shadow from a {o.height_m} m building on the northern neighbouring lot reach this property?
        </p>
        <div className="space-y-0 divide-y divide-gray-50">
          <div className="grid grid-cols-[1fr_auto_auto_auto] gap-4 pb-2 text-xs font-medium text-gray-400 uppercase tracking-wide">
            <span>Date &amp; time</span>
            <span className="text-right">Reach</span>
            <span className="text-right">Direction</span>
            <span className="text-right">Coverage</span>
          </div>
          {scenarios.map((s) => {
            const pct = s.shadow_overlap_fraction != null
              ? Math.round(s.shadow_overlap_fraction * 100)
              : null;
            const coverageColor = pct == null ? 'bg-gray-100 text-gray-400'
              : pct >= 70 ? 'bg-red-100 text-red-700'
              : pct >= 40 ? 'bg-amber-100 text-amber-700'
              : pct > 0   ? 'bg-yellow-50 text-yellow-700'
              : 'bg-gray-100 text-gray-500';
            return (
              <button
                key={s.scenario}
                onClick={() => setActiveScenario(s.scenario)}
                className={`w-full grid grid-cols-[1fr_auto_auto_auto] gap-4 py-3 text-sm items-center text-left rounded transition-colors ${
                  activeScenario === s.scenario
                    ? 'bg-teal-50 -mx-2 px-2'
                    : 'hover:bg-gray-50 -mx-2 px-2'
                }`}
              >
                <span className="text-gray-700">{SCENARIO_LABELS[s.scenario] ?? s.scenario}</span>
                <span className="text-gray-500 text-xs text-right tabular-nums">
                  {s.shadow_length_m > 0 ? `${s.shadow_length_m.toFixed(0)} m` : '—'}
                </span>
                <span className="text-gray-400 text-xs text-right">
                  {s.shadow_direction_deg != null ? bearingToCompass(s.shadow_direction_deg) : '—'}
                </span>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full text-right ${coverageColor}`}>
                  {pct != null ? `${pct}%` : '—'}
                </span>
              </button>
            );
          })}
        </div>
      </div>

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
