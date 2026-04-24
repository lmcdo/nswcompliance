'use client';

import { useState } from 'react';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';
import { posthog } from '@/components/providers/PostHogProvider';

interface EmsActivation {
  activation_id: string;
  event_name: string;
  event_date: string;
  flood_type: string;
}

interface FloodOutputs {
  epi_flood_class: string | null;
  epi_flood_label: string | null;
  sar_flood_detected: boolean | null;
  sar_confidence: string | null;
  sar_analysis_date: string | null;
  ems_flood_detected: boolean | null;
  ems_activations: EmsActivation[] | null;
  jrc_water_occurrence_pct: number | null;
  jrc_data_year: number | null;
  bom_gauge_name: string | null;
  bom_gauge_distance_km: number | null;
  bom_last_major_flood_date: string | null;
  bom_last_major_flood_peak_m: number | null;
  s1_gap_warning: string | null;
  data_currency: string;
  flood_signal: 'none' | 'low' | 'moderate' | 'elevated' | null;
}

interface FloodResult {
  address: string;
  lat: number;
  lng: number;
  run_date: string;
  outputs: FloodOutputs;
  confidence: string;
  data_sources: string[];
  warnings?: string[];
}

type PageState = 'idle' | 'running' | 'complete' | 'error';

const FLOOD_SIGNAL_META: Record<string, { label: string; sublabel: string; badge: string; bar: string }> = {
  none:     {
    label:    'No flood indicators detected',
    sublabel: 'No signals across any data source',
    badge:    'bg-green-100 text-green-800',
    bar:      'bg-green-500',
  },
  low:      {
    label:    'Low flood signal',
    sublabel: 'Statutory overlay only — no observed events on record',
    badge:    'bg-yellow-100 text-yellow-800',
    bar:      'bg-yellow-400',
  },
  moderate: {
    label:    'Moderate flood signal',
    sublabel: 'One or more data sources indicate past or potential inundation',
    badge:    'bg-orange-100 text-orange-800',
    bar:      'bg-orange-500',
  },
  elevated: {
    label:    'Elevated flood signal',
    sublabel: 'Multiple independent sources converge on flood exposure',
    badge:    'bg-red-100 text-red-800',
    bar:      'bg-red-500',
  },
};

const EPI_CLASS_META: Record<string, { label: string; color: string }> = {
  high_flood_risk:     { label: 'High flood risk zone',   color: 'bg-red-50 text-red-700' },
  medium_flood_risk:   { label: 'Medium flood risk zone', color: 'bg-orange-50 text-orange-700' },
  low_flood_risk:      { label: 'Low flood risk zone',    color: 'bg-yellow-50 text-yellow-700' },
  flood_planning_area: { label: 'Flood planning area',    color: 'bg-blue-50 text-blue-700' },
  none:                { label: 'Not in statutory flood overlay', color: 'bg-green-50 text-green-700' },
};

export function FloodTool({ lgaSlug, embedRef }: { lgaSlug?: string; embedRef?: string }) {
  const [address, setAddress] = useState('');
  const [state, setState] = useState<PageState>('idle');
  const [result, setResult] = useState<FloodResult | null>(null);
  const [errorMsg, setErrorMsg] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!address.trim()) return;
    setState('running');
    setResult(null);
    setErrorMsg('');

    try {
      const res = await fetch('/api/satellite/flood', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address }),
      });
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || 'Flood analysis failed');
      setResult(json);
      setState('complete');
      posthog.capture('tool_run', {
        tool: 'flood-truth',
        source: embedRef ? 'embed' : lgaSlug ? 'lga_page' : 'direct',
        embed_ref: embedRef ?? null,
        lga_slug: lgaSlug ?? null,
        result: json.outputs?.flood_signal ?? null,
      });
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Unknown error');
      setState('error');
    }
  };

  return (
    <div className="mb-8">
      <h1 className="text-2xl font-bold text-gray-900">Flood Data Summary</h1>
      <p className="mt-1.5 text-sm text-gray-500">
        Cross-references NSW EPI statutory flood overlays, Copernicus EMS observed events,
        40-year Landsat water history, and BOM river gauge data for any NSW address.
        Indicative only — not a substitute for a formal Section 10.7 flood certificate.
      </p>

      <form onSubmit={handleSubmit} className="flex gap-3 mt-6 mb-8">
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
          {state === 'running' ? 'Checking...' : 'Run Flood Check'}
        </button>
      </form>

      {state === 'running' && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 flex flex-col items-center text-center">
          <div className="w-8 h-8 border-2 border-teal-600 border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-sm font-medium text-gray-700">Querying flood data sources...</p>
          <p className="text-xs text-gray-400 mt-1">EPI overlay · Copernicus EMS · JRC 40yr history · BOM gauge. Allow 15–30 seconds.</p>
        </div>
      )}

      {state === 'error' && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-sm text-red-700">
          {errorMsg}
        </div>
      )}

      {state === 'complete' && result && <FloodCard result={result} />}
    </div>
  );
}

function FloodCard({ result }: { result: FloodResult }) {
  const o = result.outputs;
  const signal     = o.flood_signal ?? 'none';
  const signalMeta = FLOOD_SIGNAL_META[signal] ?? FLOOD_SIGNAL_META.none;
  const epiClass   = o.epi_flood_class ?? 'none';
  const epiMeta    = EPI_CLASS_META[epiClass] ?? { label: epiClass, color: 'bg-gray-50 text-gray-700' };
  const sourceCount = (result.data_sources ?? []).length;

  return (
    <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">

      {/* Header — flood signal as primary indicator */}
      <div className="p-6">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h2 className="font-semibold text-gray-900">{result.address}</h2>
            <p className="text-xs text-gray-400 mt-0.5">Run {result.run_date} · {sourceCount} data sources</p>
          </div>
          <span className={`shrink-0 text-xs font-medium px-2.5 py-1 rounded-full ${signalMeta.badge}`}>
            {signalMeta.label}
          </span>
        </div>
        <p className="text-xs text-gray-500">{signalMeta.sublabel}</p>
        <p className="text-xs text-gray-400 mt-1">
          Data convergence indicator across {sourceCount} independent sources.
          A formal Section 10.7 certificate from council is required for legal flood status.
        </p>
      </div>

      {/* Row 1: Council flood overlay + Copernicus observed events */}
      <div className="grid grid-cols-2 divide-x divide-gray-100">
        <div className="p-6">
          <p className="text-xs text-gray-400 mb-1">Council flood overlay</p>
          <p className={`inline-block text-sm font-medium px-2 py-0.5 rounded ${epiMeta.color} mb-1`}>
            {epiMeta.label}
          </p>
          <p className="text-xs text-gray-400">
            NSW EPI Flood WFS · data as at {o.data_currency !== 'unknown' ? o.data_currency : 'date unavailable'}
          </p>
        </div>
        <div className="p-6">
          <p className="text-xs text-gray-400 mb-1">Observed flood events</p>
          {o.ems_flood_detected === null ? (
            <p className="text-sm text-gray-400">Data not available</p>
          ) : o.ems_flood_detected && o.ems_activations?.length ? (
            <ul className="space-y-1.5">
              {o.ems_activations.map((act) => (
                <li key={act.activation_id} className="flex items-start gap-2">
                  <span className="mt-1.5 shrink-0 w-1.5 h-1.5 rounded-full bg-red-500" />
                  <div>
                    <p className="text-xs font-medium text-gray-900">{act.event_name}</p>
                    <p className="text-xs text-gray-400">{act.activation_id} · {act.event_date}</p>
                  </div>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-600">No recorded events at this location</p>
          )}
          <p className="text-xs text-gray-400 mt-2">Copernicus EMS · NSW Spatial Services</p>
        </div>
      </div>

      {/* Row 2: JRC water history + BOM gauge */}
      <div className="grid grid-cols-2 divide-x divide-gray-100">
        <div className="p-6">
          <p className="text-xs text-gray-400 mb-1">40-year surface water history</p>
          {o.jrc_water_occurrence_pct != null ? (
            <>
              <p className="text-lg font-semibold text-gray-900">
                {o.jrc_water_occurrence_pct.toFixed(0)}
                <span className="text-sm font-normal text-gray-500">% of months</span>
              </p>
              <p className="text-xs text-gray-500 mt-1">
                {o.jrc_water_occurrence_pct === 0
                  ? 'No surface water observed at this site 1984–present'
                  : o.jrc_water_occurrence_pct < 5
                  ? 'Rare — episodic inundation only'
                  : o.jrc_water_occurrence_pct < 15
                  ? 'Occasional — periodic inundation'
                  : o.jrc_water_occurrence_pct < 40
                  ? 'Frequent — seasonal or recurring inundation'
                  : 'Persistent — regular or permanent surface water'}
              </p>
            </>
          ) : (
            <p className="text-sm text-gray-400">Not available</p>
          )}
          <p className="text-xs text-gray-400 mt-2">JRC Global Surface Water · Landsat 1984–{o.jrc_data_year ?? 2021}</p>
        </div>
        <div className="p-6">
          <p className="text-xs text-gray-400 mb-1">River gauge proximity</p>
          {o.bom_gauge_name ? (
            <>
              <p className="text-sm font-semibold text-gray-900 leading-snug">{o.bom_gauge_name}</p>
              <p className="text-xs text-gray-400 mt-0.5">{o.bom_gauge_distance_km} km from property</p>
              {o.bom_last_major_flood_date ? (
                <p className="text-xs text-red-700 mt-2 font-medium">
                  Last major flood recorded: {o.bom_last_major_flood_date} — {o.bom_last_major_flood_peak_m}m peak
                </p>
              ) : (
                <p className="text-xs text-gray-400 mt-2">No major flood recorded at this gauge since 2021</p>
              )}
            </>
          ) : (
            <p className="text-sm text-gray-400">No BOM gauge within 75 km</p>
          )}
          <p className="text-xs text-gray-400 mt-2">BOM WaterConnect · SOS2 API</p>
        </div>
      </div>

      {/* SAR — shown only when data available */}
      {o.sar_flood_detected !== null && (
        <div className="px-6 py-4">
          <p className="text-xs text-gray-400 mb-1">Satellite SAR flood detection</p>
          <p className="text-sm font-medium text-gray-900">
            {o.sar_flood_detected ? 'Flood signal detected' : 'No flood signal detected'}
            {o.sar_confidence && <span className="font-normal text-gray-500"> — {o.sar_confidence} confidence</span>}
          </p>
          <p className="text-xs text-gray-400 mt-0.5">Sentinel-1 RTC · Microsoft Planetary Computer{o.sar_analysis_date ? ` · ${o.sar_analysis_date}` : ''}</p>
        </div>
      )}

      {/* Warnings */}
      {(o.s1_gap_warning || result.warnings?.length) && (
        <div className="px-6 py-4 bg-amber-50 space-y-1">
          {o.s1_gap_warning && <p className="text-xs text-amber-800">{o.s1_gap_warning}</p>}
          {result.warnings?.map((w, i) => (
            <p key={i} className="text-xs text-amber-800">{w}</p>
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="px-6 py-4">
        <p className="text-xs text-gray-400">
          Sources: {(result.data_sources ?? []).join(' · ')}
        </p>
        <p className="text-xs text-gray-400 mt-0.5">
          Indicative only. Not a substitute for a formal Section 10.7 flood certificate.
          Consult council or a qualified flood engineer for development or conveyancing decisions.
        </p>
      </div>
    </div>
  );
}
